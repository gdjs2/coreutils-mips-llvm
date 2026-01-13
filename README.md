# Coreutils MIPS Bianry - Data & Code Separation Dataset

## How to use?

1. Clone this repo:  
```git clone https://github.com/gdjs2/coreutils-mips.git```
2. Update submodules:  
```git submodule update --init --recursive```
3. Fill `.env` file with your user information for creating docker compose. Check `.env` file for more information. 
4. Up the docker compose: ```docker compose up``` or `docker compose up -d` if you want to make it in background. 
5. Attach to the docker container by: `docker exec -it {YOUR DOCKER ID or HASH}` bash
6. Go to workspace: `cd /workspace`
7. Build the binaries (nonstripped & stripped): `./build_mips.py`
8. Generate ground truths using non-stripped binaries: `./create_mips_dataset.py`