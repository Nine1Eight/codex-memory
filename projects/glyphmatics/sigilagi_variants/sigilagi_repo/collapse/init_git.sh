mkdir -p ~/sigilagi_repo
cp -rf ~/sigilagi_real ~/sigilagi_repo/
cp -rf ~/collapse ~/sigilagi_repo/
cp -f ~/sigilagi_real_capsule.py ~/sigilagi_repo/
cd ~/sigilagi_repo || exit 1
git init
git branch -M main
git add .
git commit -m "Freeze v4 deterministic capsule pipeline"
git status
