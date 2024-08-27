#!/bin/bash

env_file=$1

while IFS= read -r line; do
  export "$line"
done < "$env_file"
