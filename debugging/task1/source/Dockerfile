FROM ubuntu:20.04

RUN apt -y update
RUN apt -y upgrade
RUN apt install -y build-essential

ENV DEBIAN_FRONTEND=noninteractive

RUN apt install -y cmake
RUN apt install -y wget
RUN apt install -y unzip
RUN apt install -y bear
RUN apt install -y curl

RUN apt install -y llvm-10 llvm-10-dev llvm-10-tools clang-10 libclang-10-dev

WORKDIR /app

COPY . .

RUN mkdir -p build
RUN cd build && cmake .. && make -j4
RUN cd example && make clean && bear make

CMD ["/bin/bash", "-c", "cd example && ../build/parsec *.c"]