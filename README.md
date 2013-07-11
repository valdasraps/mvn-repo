mvn-repo
========

Valdas Rapsevicius Maven repository

Instructions on how to add new artifacts:

1. clone repository

git clone https://github.com/valdasraps/mvn-repo.git

2.1. add single 3rd party jar file:

mvn deploy:deploy-file -DgroupId=org.cern.dim -DartifactId=dim -Dversion=20.7 -Dpackaging=jar \
    -Dfile=dim.jar -Durl=file:///home/valdo/Documents/mvn-repo/releases
    
2.2. add maven project as artifact:

mvn -DaltDeploymentRepository=repo::default::file:../mvn-repo/releases clean deploy

3. commit 

git commit -a -m "dim-20.7.jar"

4. push to github

git push origin master
