import os
import asmsa
import numpy as np
import matplotlib.pyplot as plt
import time
import mdtraj as md
import nglview as nv
import gromacs as gmx
import joblib #parallelize updatings

from PIL import Image
from IPython.display import display, clear_output
from matplotlib.colors import Normalize
from functools import lru_cache
from datetime import datetime, timedelta

class Analysis:
    
    def __init__(self, conf, traj, hills, lows_filename):

        self.hills = hills
        self.lows_filename = lows_filename
        self.conf = conf
        self.traj = traj
    
    def latent_space(self):

        tr = md.load(self.traj,top=self.conf)
        lows = np.loadtxt(self.lows_filename)
        base = md.load(self.conf)
        lows_rmsd = md.rmsd(tr,base[0]) 
        return lows, lows_rmsd

    def preapre(self):
                
        gmx.trjconv(f='md.xtc',s='npt.gro',input='Protein-H',o='protein.xtc')
        gmx.trjconv(f='protein.xtc',s=f'npt_nh.pdb',pbc='nojump',input='Protein-H',o='MD_pbc.xtc')
        gmx.trjconv(f='MD_pbc.xtc',s=f'npt_nh.pdb',center=True,fit='rot+trans',input='Protein-H Protein-H Protein-H'.split(),o='MD_fit.xtc')

        conf_nh = "npt_nh.pdb"
        traj_fit = "MD_fit.xtc"

        return conf_nh, traj_fit
    
    # Cache from HILLS
    @lru_cache(maxsize=None)
    def load_hills(hills):
        return np.loadtxt(hills)

    def read_last_step_time(self, filename='md.log'):
        last_step = None
        last_time = None
        with open(filename, 'r') as file:
            lines = file.readlines()
            for i in range(len(lines)-1, -1, -1):
                if "Step" in lines[i] and "Time" in lines[i]:
                    last_step, last_time = lines[i+1].split()
                    break
        return last_step, last_time


            
    
    def on_the_flight(self, interval=60, cmap='rainbow'):
        
        """
        Script for 'on the flight' visualization of enhanced 
        molecular dynamics simulation 
    
        File: 
            - .xtc trajectory from gromacs
            - Hills file form metadynamics (plumed hills output)
            - COLVAR file from metadynamics (plumed colvar output)
            - Reference latent space image
        Args:
            - interval (float): time to update the visualization with a new bench of frames
            - image_filename (str): referece latent space image name. Default: 'rmsd_lows.png'.
    
        """
     
        file_path = 'HILLS'

        lows, lows_rmsd = self.latent_space()
        
        plt.ion()
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 10))
    
        l1, l2 = lows[:,0], lows[:,1]

        try:
            hills_data = None
            last_length = 0
            while True:

                file_path = 'md.log'

                if os.path.exists(file_path):
                    
                    last_modified = os.path.getmtime(file_path)
                    current_time = datetime.now().timestamp()
                    seconds_ago = current_time - last_modified
                    
                    if seconds_ago < 300:
                        print(f"Running...")
                    else:
                        print(f"No running...")
    
                    new_hills = np.loadtxt(self.hills, skiprows=last_length)
                    if new_hills.size > 0:
                        if hills_data is None:
                            hills_data = new_hills
                        else:
                            hills_data = np.vstack((hills_data, new_hills))
                        last_length = hills_data.shape[0]
    
                t = hills_data[:, 0] / 1000
                cv1, cv2, hh = hills_data[:, 1], hills_data[:, 2], hills_data[:, 5]
    
                last_step, last_time = self.read_last_step_time()
                times = float(last_time) / 1000
    
                ax1.clear()
                ax1.plot(t, cv1, 'b-', label='cv1', linewidth=0.5)
                ax1.plot(t, cv2, 'g-', label='cv2', linewidth=0.5)
                ax1.set_title(f'Time: {times}ns')
                ax1.legend()
    
                ax2.clear()
                ax2.scatter(cv1, cv2, c=t, cmap=cmap, marker='.', s=1, zorder=1)
                ax2.scatter(cv1[-1], cv2[-1], c='black', marker='x', s=25, zorder=1)
                ax2.scatter(cv1[0], cv2[0], c='black', marker='o', s=25, zorder=1)
                ax2.scatter(lows[:,0], lows[:,1], c='gray', marker='.', s=1, zorder=0)
                
                ax2.set(xlabel='cv1', ylabel='cv2')
                ax2.set_title(f'o: reference structure           x: {last_step}step ')
    
                ax3.clear()
                ax3.scatter(t, hh, c=t, cmap=cmap, marker='.', s=5)
                ax3.set_title(f'Hills')
                ax3.set(xlabel='time(ns)')
                ax3.set(ylabel='high hills')
    
                l1, l2 = lows[:,0], lows[:,1]
                
                ax4.clear()
                ax4.scatter(lows[:,0], lows[:,1], c=lows_rmsd, cmap=cmap, marker='.', s=5)
                ax4.scatter(l1[0], l2[0], c='black', marker='o', s=25)
                ax4.set_title(f'AEE - Latent Space')
                ax4.set(xlabel='cv1')
                ax4.set(ylabel='cv2')
    
                display(fig)
                clear_output(wait=True)
                time.sleep(interval)
        except KeyboardInterrupt:
            plt.ioff()


    
    def highlights(self, time=1000, cmap='rainbow'):

        conf_nh, traj_fit = self.preapre()
        
        new_hills = np.loadtxt(self.hills)
        tr = md.load(traj_fit, top=conf_nh)
        idx = tr.top.select("name CA")
    
        t = new_hills[:, 0] / 1000
        cv1, cv2 = new_hills[:, 1], new_hills[:, 2]
    
        for i in range(0, len(cv1), time):
            clear_output(wait=True)
            plt.figure(figsize=(10, 5))
            plt.scatter(cv1, cv2, c='grey', marker='.', s=0.1)
            plt.scatter(cv1[:i+1], cv2[:i+1], c=t[:i+1], cmap=cmap, marker='.', s=1)
            plt.title(f'{t[i]:.0f}ns')
            plt.pause(0.0001)
    
        plt.show()
    
    def look_dynamic(self):

        conf_nh, traj_fit = self.preapre()

        tr = md.load(traj_fit, top=conf_nh)
        idx = tr.top.select("name CA")
        tr.superpose(tr, atom_indices=idx)
        
        v = nv.show_mdtraj(tr, default=False, gui=False)
        v.add_cartoon(selection="protein", color='red')
        c = v.add_component(tr[0], default=False, gui=False)
        c.add_cartoon(selection="protein", color='blue')
        v.add_line("trp", color='yellow')
        c.add_line("trp", color='orange')
        v.center(selection='protein')
        v.render_image(trim=True, factor=3)
        v.camera = 'orthographic'
        v.background = 'white'
        display(v)
        
    def rmsd (self):

        conf_nh, traj_fit = self.preapre()
       
        tr = md.load(traj_fit, top=conf_nh)
        #idx=tr.top.select("name CA")
        #tr.superpose(tr,atom_indices=idx)
        plt.figure(figsize=(10,4))
        rmsds = md.rmsd(tr, tr, 0,precentered=True) #atom_indices=idx,ref_atom_indices=idx, 
    
        plt.title(f'TrpCage RMSD - {int(tr.time[-1]/1000)} ns')
        plt.scatter(tr.time/1000,rmsds,c=rmsds, s=0.1, cmap='jet')
        #plt.show()
        plt.savefig('rmsd.png')