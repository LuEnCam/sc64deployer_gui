## On linux machines: 
1) do: sudo nano /etc/sudoers

2) add at the bottom:
```
username ALL=([YOUR_USERNAME]) NOPASSWD: /home/[YOUR_USERNAME]/github/sc64deployer_gui/sc64deployer
```