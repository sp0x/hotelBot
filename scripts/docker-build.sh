#!/bin/bash
set -e

cd /tmp/$IMAGE

sudo docker build -t $NAME .
sudo docker tag $NAME $REGISTRY/$IMAGE
sudo docker push $REGISTRY/$IMAGE
echo "Built and pushed $REGISTRY/$IMAGE"
