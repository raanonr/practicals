#!/bin/bash

echo "Cleaning ... "
rm -rf data
#rm -rf output/*

echo "unziping archives ..."
#unzip -q 'input/*' -d output

create_training () {
	mkdir -p data/train/$1s
	mkdir -p data/validation/$1s
	
	echo "Created file with $1s names ... "
	ls output/*/$1* > output/$1s.txt
	shuf -n 1400 output/$1s.txt > output/$1s_$2.txt

	echo "Copying $1s train subset"
	cat output/$1s_$2.txt | head -1000 | xargs cp -t data/train/$1s
	
	echo "Copying $1s validation subset"
	cat output/$1s_$2.txt | tail -400  | xargs cp -t data/validation/$1s

	echo "Created $1s training subset."
}

create_training dog 1000
create_training cat 1000

echo "Created data."
