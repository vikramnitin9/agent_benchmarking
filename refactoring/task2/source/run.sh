# Usage ./run.sh <dataset_name> <model_name>
# <dataset_name> must be in data/datasets.json and <model_name> must be in translation_gym/models/__init__.py
docker run -it translation_gym:latest python main.py --dataset $1 --model $2 --output_dir /app/output/$1
