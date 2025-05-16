docker build . -t mycontainer:latest

mkdir -p output
docker run -it \
    -u $(id -u):$(id -g) \
    -v $PWD/output:/app/output \
    mycontainer:latest \
    python hello.py