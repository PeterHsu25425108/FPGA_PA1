# bash script to copy Makefile, report.pdf, and the entire /src directory to the /submission directory
#!/bin/bash

# if submission directory doesn't exist, create it, else clear its contents
if [ ! -d "submission" ]; then
  mkdir submission
else
  rm -rf submission/*
fi
# convert Report.md to report.pdf using pandoc
pandoc Report.md -o report.pdf
cp Makefile submission/
cp report.pdf submission/
cp -r src/ submission/
# zip them into 314510144.zip
cd submission
zip -r ./314510144.zip .
cd ..