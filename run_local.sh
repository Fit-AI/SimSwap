#!/bin/bash

for fullfile in $(ls ~/Desktop/3_cl6f6al3n001109gv3aacnd7y-walking/*.png); do 
  time python test_wholeimage_swapsingle.py --crop_size 512     \
                                            --use_mask          \
                                            --name people       \
                                            --Arc_path arcface_model/arcface_checkpoint.tar \
                                            --pic_a_path /home/ian/jlo.jpg                  \
                                            --pic_b_path $fullfile     \
                                            --output_path ./output/
  filename=$(basename -- "$fullfile")
  extension="${filename##*.}"
  filename="${filename%.*}"
  #echo $fullfile
  #echo $filename
  #echo $extension
  mv output/result_whole_swapsingle.jpg output/$filename.jpg
  #break
done
