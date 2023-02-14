FROM python:3.9-slim as builder

ENV DEBIAN_FRONTEND=noninteractive 
ENV TZ=Europe/Prague

RUN apt update && apt install -y git g++ libz-dev tini procps && apt clean && rm -rf /var/lib/apt/lists/*

COPY start-notebook.sh /usr/local/bin/

RUN useradd -m -u 1000 jovyan
RUN mkdir -p /opt && chown jovyan /opt

USER jovyan
WORKDIR /opt

# torch & torchvision must be compatible with gromacs container
RUN python -m venv . 
RUN . bin/activate && pip install \
tensorflow \
torch==1.12.1 \
torchvision==0.13.1 \
mdtraj \
keras_tuner \
jupyterhub \
jupyterlab \
matplotlib \
"ipywidgets<8" \
nglview \
networkx \
sympy onnx2torch \
&& rm -r /home/jovyan/.cache

RUN . bin/activate && pip install git+https://github.com/onnx/tensorflow-onnx && rm -r /home/jovyan/.cache

RUN . bin/activate && jupyter-nbextension enable nglview --py 

COPY dist/asmsa-0.0.1.tar.gz /tmp
RUN . bin/activate && pip3 install /tmp/asmsa-0.0.1.tar.gz && rm -r /home/jovyan/.cache

RUN . bin/activate && pip3 install kubernetes dill && rm -r /home/jovyan/.cache

USER root
RUN apt update && apt install -y curl && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && install -m 755 kubectl /usr/local/bin && apt clean && rm -rf /var/lib/apt/lists/*

USER jovyan

RUN mkdir /opt/ASMSA
COPY IMAGE prepare.ipynb tune.ipynb train.ipynb md.ipynb /opt/ASMSA/
COPY md.mdp.template *.mdp /opt/ASMSA/
COPY tuning.py tuning.sh /usr/local/bin/
WORKDIR /home/jovyan

ENTRYPOINT ["tini", "-g", "--"]
CMD ["start-notebook.sh"]
