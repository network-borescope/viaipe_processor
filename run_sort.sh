#!/bin/bash

if [ $# != 1 ]
then
	echo "Missing argument: <path>"
	exit 1
fi

DIR_PATH=$1
DST_PATH="sorted_tc"
mkdir ${DST_PATH}

COMMAND=`find $DIR_PATH -type f`

for full_filename in $COMMAND
do
	FILENAME=`echo ${full_filename} | cut -d "/" -f 4`
	sort ${full_filename} | uniq | sed '/^\#/d' > "$DST_PATH/$FILENAME"
done
