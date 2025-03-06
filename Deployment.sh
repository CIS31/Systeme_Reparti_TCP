#!/bin/bash

login="login"
localFolder="./"
todeploy="Folder_To_Deploy"
remoteFolder="remoteFolder"
nameOfTheScript="Worker.py"

# Lire les machines à partir du fichier Workers.txt
computers=($(cat Workers.txt))

# Transferer le dossier à déployer
command1=("ssh" "-tt" "$login@${computers[0]}" "rm -rf $remoteFolder; mkdir $remoteFolder;wait;")
echo ${command1[*]}
"${command1[@]}";wait;

command2=("scp" "-r" "$localFolder$todeploy" "$login@${computers[0]}:$remoteFolder")
echo ${command2[*]}
"${command2[@]}";wait;

for c in ${computers[@]}; do
  # Lance le script sur chaque machine
  command3=("ssh" "-tt" "$login@$c" "cd $remoteFolder/$todeploy; python3 $nameOfTheScript; wait;")

  echo ${command3[*]}
  "${command3[@]}" &
done