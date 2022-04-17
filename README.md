# qlbry
A basic client for LBRY and Odysee! Still kind of early in development, so it doesn't have too many features yet

## Usage

### Linux

1) Download the latest release [here](https://github.com/AprilDolly/qlbry/releases/tag/stuff).

2) In a terminal, type `chmod +x qlbry.AppImage`

3) Double click to run it, or type `./qlbry.AppImage` in the terminal.

### Windows

Will come soon. For now, you will have to download python and manually install the dependencies, I'm afraid :c

### Using from source

1) run `git clone https://github.com/AprilDolly/qlbry.git`
2) run `cd qlbry`
3) run `pip3 install -r requirements` (use pip instead of pip3 if python3 is your only python installation and this doesn't work)
4) [Download the latest lbrynet executable](https://github.com/lbryio/lbry-sdk/releases) if it is not already installed, then place the "lbrynet" file in the qlbry directory or add it to your system's PATH variable.
5) run `python3 -m qlbry.py` to start the client.
