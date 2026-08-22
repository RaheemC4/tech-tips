# GPU OVERCLOCK

*Category: Overclocking | Originally posted: 2022-09-16 | 2 message(s)*

MSI AFTERBURNER
https://download.msi.com/uti_exe/vga/MSIAfterburnerSetup.zip?__token__=exp=1700987929~acl=/*~hmac=160152d7ad3ad8a1b7f1d78c437ab1854d7ba93e7809664af11fe1150142e0eb


Download MSI Afterburner, setting both power limit and temp limit to max. A good starting overclock is about +100 core and +400 memory. u can increase these values but do so in small increments
 


Core Overclock: Increase in increments of +30 then play a game, if it is stable increase by +30 again. Rinse and repeat until you start getting graphical issues in game then decrease your core by 15 and see if that is stable



Memory Overclock: Move onto increasing memory clock once you have reached a stable coe clock. Increase in increments of +100 then play a game, if it is stable increase by +100 again. Rinse and repeat until you start getting graphical issues in game then decrease your core by 50 and see if that is stable

![unknown.png](https://cdn.discordapp.com/attachments/1020276068084621382/1020276068449521714/unknown.png?ex=6a8ac7a2&is=6a897622&hm=10b0cc5712867937eaadf6ccd5125ce1c3944dfb923a89d0615b59c496d23175&)

---
**Raheem** (2024-06-01):

**NVIDIA**

MSI Afterburner:
Just use afterburner every other software is terrible. 

Power:
Max out your power and temp limit to limit the amount of downclocking that might happen. This is more important for 20/30 series GPUs. 

Voltage:
Go to settings in Afterburner and check “unlock voltage control” and “allow voltage monitoring”. It will ask you to restart afterburner. After this max out the core voltage slider to +100. This will allow the whole voltage range to be used by your gpu and allow for higher core clocks. 

Core:
I would not recommend using the curve lock method anymore. It has worse effective clocks when tested and causes for higher power draw. Instead set an offset. Start at +15 and increase by 15mhz each time until unstable. Nvidia GPUs frequency changes in 15 mhz increments. Use timespy and timespy extreme to validate stability

VRAM:
You must see what results are with stock vram oc. Then increase the vram by +100 MHz noting the score each time. At a certain point even though it is stable it will get a lower score meaning it is error correcting and you need to lower your vram clock.
