FROM nvidia/cuda:11.3.0-devel-ubuntu20.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update &&                   \
    apt-get install -y build-essential  \
                       python3          \
                       python3-pip      \
                       libopencv-dev

RUN pip3 install torch==1.12.0 torchvision==0.13.0          \
                 --ignore-installed imageio                 \
                 insightface==0.2.1 onnxruntime moviepy     \
                 protobuf==3.20.0                           \
                 requests flask

WORKDIR /app
COPY models/ /app/models
COPY options/ /app/options
COPY util/ /app/util
COPY insightface_func/ /app/insightface_func
COPY parsing_model/ /app/parsing_model
COPY simswaplogo/ /app/simswaplogo
COPY arcface_model/ /app/arcface_model
COPY checkpoints/ /app/checkpoints
RUN pip3 install gunicorn munch supabase
COPY service.py /app
COPY run.sh /app
COPY default_configuration.json /app/

ARG SUPABASE_URL_ARG
ENV SUPABASE_URL=$SUPABASE_URL_ARG

ARG SUPABASE_KEY_ARG
ENV SUPABASE_KEY=$SUPABASE_KEY_ARG

CMD ["./run.sh"]
