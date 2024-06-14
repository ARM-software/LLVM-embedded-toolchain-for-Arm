FROM ubuntu:22.04
LABEL maintainer "Pawel Wodnicki <pawel@32bitmicro.com>"

RUN apt-get -o Acquire::ForceIPv4=true update && apt-get -o Acquire::ForceIPv4=true install -y \
    build-essential \
    git \
    cmake \
    ninja-build \
    make \
    llvm llvm-dev \
    clang clang-tools \
    lldb \
    lld \
    libc++-dev libc++abi-dev \
    python3-minimal python3-pip\
    wget \
    software-properties-common

ADD build-from-repos.sh  /tmp

RUN /tmp/build-from-repos.sh