FROM ubuntu:22.04
LABEL maintainer "Pawel Wodnicki <pawel@32bitmicro.com>"
LABEL org.opencontainers.image.source=https://github.com/32bitmicro/LLVM-Embedded-Toolchain
LABEL org.opencontainers.image.description="LLVM Embedded Toolchain LLVM-ETOOOL image"
LABEL org.opencontainers.image.licenses=Apache


RUN apt-get -o Acquire::ForceIPv4=true update && apt-get -o Acquire::ForceIPv4=true install -y \
    build-essential \
    git \
    cmake \
    ninja-build \
    make \
    python3-minimal python3-pip\
    wget \
    software-properties-common
