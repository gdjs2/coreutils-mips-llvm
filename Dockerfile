FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    crossbuild-essential-mips \
    build-essential \
    autoconf \
    automake \
    libtool \
    pkg-config \
    make \
    wget \
    git \
    vim \
    bison \
    flex \
    texinfo \
    gettext \
    autopoint \
    gperf \
    python3-full

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip3 install --no-cache-dir \
    loguru==0.7.3 \
    pyelftools==0.32 \
    r2pipe==1.9.6 \
    tqdm==4.67.1

RUN git clone https://github.com/radareorg/radare2 /tmp/radare2 \
    && /tmp/radare2/sys/install.sh

RUN mkdir -p /opt/llvm && \
    cd /opt && \
    wget -q https://github.com/llvm/llvm-project/releases/download/llvmorg-21.1.0/LLVM-21.1.0-Linux-X64.tar.xz && \
    tar -xJf LLVM-21.1.0-Linux-X64.tar.xz && \
    mv LLVM-21.1.0-Linux-X64/* /opt/llvm/ && \
    rm -rf LLVM-21.1.0-Linux-X64 LLVM-21.1.0-Linux-X64.tar.xz

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USERNAME=root

RUN groupadd -g ${GROUP_ID} ${USERNAME} && \
    useradd -m -u ${USER_ID} -g ${GROUP_ID} -s /bin/bash ${USERNAME}

USER ${USERNAME}
WORKDIR /home/${USERNAME}

CMD ["/bin/bash"]