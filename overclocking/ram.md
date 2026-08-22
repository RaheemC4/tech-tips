# RAM

*Category: Overclocking | Originally posted: 2022-09-16 | 11 message(s)*

RAM is a very underlooked component in a PC. It plays a large part in performance gains when you are not GPU bottlenecked, A.K.A at 1080p/1440p.
 

Overclocking RAM may seem extremely difficult and you may think it can lead to blowing up your system or breaking it. I can assure you that modern day PCs will not blow up and even if you enter a value for the memory that is unstable or completely wrong, the motherboard has protocols in place such as the ability to reset its CMOS to get everything back up again. It is quite easy to reset the CMOS on most boards so do not worry about any risks. If you follow the guides/information within this post you will have no issues and you will get that sweet FPS boost


Do not buy cheap Corsair Vengeance RAM or anything that is cheap, they have garbage binnings for the memory chips meaning you will get lower performance generally as they have looser timings and they usually have crappy Micron or Hynix chips that are terrible at overclocking


Try to increase your budget a bit more and get some RAM sticks that are Samsung B-die binned which have the best oveclocking capability for DDR4 memory.These are on the higher end of memory prices with the cheapest kit of 16GB (2x8GB) being the Patriot Viper Steel 4000MHz 16-16-16-36 at around £80-100. I highly recommend this kit if you want the best performance and dont mind 16GB of memory


You can get more expensive kits which are 32GB(2x16GB) but you are going to have to do research to check they are Samsung B-die


For memory overclocking, you generally want to get higher end motherboards that have better VRM heatsinks to allow easier stability with lower voltages but it isnt essential. Some more expensive motherboards also have access to tweak more timings than others which arent very common but you arent missing out on much by not having a £300+ motherboard



RAM Frequency Speed is dependent on the quality of the motherboard and RAM Cas Latency (CL) is dependent on the cpu memory controller. So if you arent reaching a higher frequency it is because of your motherboard and if you cant get the cas latency any lower it is because of the memory controller on the cpu

https://youtu.be/BUtMhVl1-Bs?t=603

> **NEWEGG PREBUILT GAMING PC, WARZONE FPS BENCHMARK**
> https://www.youtube.com/watch?v=BUtMhVl1-Bs&start=603
> How much FPS can you squeeze out of a prebuilt??  Do they all suck? should you BUY or BUILD

---
**Raheem** (2022-09-16):

**DDR4 BDIE**


Here are the best PLUG AND PLAY RAM for both platforms. this way u wont need to manually change any timings. you can just put XMP on and you will be good. downside to these RAMs are that they are more expensive than looser B-die like the Vipers cuz u dont have to manually change anything.


**For AMD 3000+ CPUs : **
https://www.amazon.co.uk/G-SKILL-Trident-2X8GB-DDR4-3600-Arbeitsspeicher/dp/B07Z95KV5X

the best plug and play xmp for AMD are the 3600mhz c14. you cant go above 3600mhz stable on AMD due to fabric instability on the cpu that i wont go into. trust youll get loads of fps with this


**For Intel 8th gen+ CPUs**
https://www.amazon.co.uk/gp/product/B09BDCP4XZ

the best is 4000mhz+ at c17 and below. these are c16. theyll do nicely. u can put xmp on and its happy days.

---
**Raheem** (2022-09-16):

**Common BDIE Timings**


common Bdie specs include but are not limited to
3200-14-14-14
3600-16-16-16
3600-14-x-x
3800-14-x-x
4000-15-x-x
4000-16-x-x
4000-17-x-x
4000-18-x-x
4000-19-19-19
4133-17-17-17
4133-19-19-19
4266-17-18-18
4266-19-19-19
4400-17-18-18
4400-18-19-19
4400-19-19-19
plus less perfect looking specs like some 4000+ Kits that have Primaries like 17-18-18 or 16-17-17 or 15-16-16, Etc

the Kits that have XMP voltages of 1.45v+ might be a bit harder to use than the rest, but otherwise they're all effectively the same and you can just price compare between them.
(4x16/4x8 forces you to run the RAM somewhat slower as it is much harder for the internal memory controller on the cpus to run 4 sticks of RAM than it is 2 , 2x16 are ideal currently)

---
**Raheem** (2022-09-16):

https://kingfaris.co.uk/blog/intel-ram-oc-impact/fortnite#fps

> **PCBuilding**
> https://kingfaris.co.uk/blog/intel-ram-oc-impact/fortnite
> KingFaris10's Site

---
**Raheem** (2022-09-17):

https://youtu.be/Ke_JgL8gxsA

> **DDR4 Overclocking/Buying absolute basics**
> https://www.youtube.com/watch?v=Ke_JgL8gxsA
> AHOC Patreon/Shirts/Paypal/Junkyard:http://cxzoid.blogspot.co.uk/p/support-fail.html

---
**Raheem** (2022-09-18):

https://youtu.be/7Gm_nw4zSDk

> **40 Year Old Boomer Goes Postal Over i3 12100.**
> https://www.youtube.com/watch?v=7Gm_nw4zSDk
> The Final Nail In Hardware Unboxed' Coffin

---
**Raheem** (2022-09-20):

Samsung DDR4 B-die Timings Ryzen


If you're very lazy and your kit has a 3200mhz 14-14 , 4000mhz 19 19 19 or better XMP I'd be very surprised if the following settings don't work for you.


**Not all the options below will show in your BIOS as some are brand limited and some are only shown on more expensive motherboards. If you dont see one in your BIOS skip it and move to the next value**


FCLK Fabric Clock: 1866
MCLK DRAM Frequency: 3733
DRAM Voltage: 1.45V
SOC Voltage: 1.1V
Gear Down Mode: Enabled

tCL: 16
tRCDWR: 16
tRCDRD: 16
tRP: 16
tRAS: 28

tRC: 44
tRRD_S: 4
tRRD_L: 6
tFAW: 16
tWTR_S: 4
tWTR_L: 8
tWR: 10
tRFC: 300

tRDRDSCL: 2
tWRWRSCL: 2
tCWL: 16
tRTP: 8
tRDWR: AUTO
tWRRD: AUTO
tRDRDSC: 1
tRDRDSD: 4
tRDRDDD: 4
tWRWRSC: 1
tWRWRSD: 6
tWRWRDD: 6
tCKE: 1


**If your PC doesnt boot or you get instabilities such as freezes and blue screens change these values:
FCLK Fabric Clock: 1800
MCLK DRAM Frequency: 3600
tCL: 16
tRCDWR: 16
tRCDRD: 16
tRP: 16
tRAS: 30
**

---
**Raheem** (2023-06-14):

https://www.patreon.com/posts/84547490

---
**Raheem** (2024-06-01):

DDR5: A-Die is the newest memory ic from Hynix and allows for higher frequencies. This is very good for 12th and 13th Gen Intel CPUs. 


A-Die:
7200: https://amzn.to/49dlvnL
8200: https://amzn.to/4cxjoy1


DDR5 Starter Voltages:

SA: 1.15-1.25 (test in that range)
CPU VDDQTX: 1.35v
VDD2/MC: 1.45
VDD (Dram Voltage): 1.45 (need pmic unlock) 1.435v w/o
VDDQ: 1.45v (need pmic unlock) 1.435v w/o

> **Computer Memory Ram RGB Hynix A-die KingBank DDR5 32GB(2x16GB) 7200...**
> https://amzn.to/49dlvnL
> memory

> **Patriot Viper Xtreme 5 DDR5 RAM 32GB (2X16GB) 8200MT/s CL38 UDIMM D...**
> https://amzn.to/4cxjoy1
> If you're passionate about IT and electronics , like being up to date on technology and don't miss even the slightest details, buy Patriot Memory PVX532G82C38K DDR5 32 GB RAM Memory at an unbeatable price. Memory type: DDR5 Format: 2 x 16 GB Latency: CL38 Speed: 8200 MHz Capacity: 32 GB

---
**Raheem** (2024-06-01):

A-Die Timings 2x16GB (32GB)

Voltages:
SOC - 1.25v
DRAM VDD - 1.43v
DRAM VDDQ - AUTO
VDDIO - AUTO
VDDP - 0.95v

Memory Frequency: 6000Mhz

**Primaries**
TCL 30
TRCD 36
TRCD_WR 16
TRP 32
TRAS 126
TRC 60
TWR 48
TRFC 400
TRFC2 400
TRFCPB 300
TREFI 65535

**Secondaries**
TRRD_S 4
TRRD_L 8
TRTP 12
TFAW 20
TWTR_S 4
TWTR_L 14

**Tertiaries**
TRDRDSCL 4
TRDRDSC 1
TWRWRSCL 2
TWRWRSC 1
TWRRD 4
TRDWR 16

**DRAM Training Configuration**
Round Trip Latency ENABLED

---
**Raheem** (2024-06-01):

I would recommend 2x24gb kits for almost anyone now. They are more expensive but the performance and ram increase is good. 

7200 non rgb: https://www.amazon.co.uk/TEAMGROUP-T-Create-Overclocking-7200MHz-PC5-57600-Black-UDIMM/dp/B0C4NNRC56


M-Die Timings 2x24 (48GB)

Voltages:
SOC - 1.25v
DRAM VDD - 1.43v
DRAM VDDQ - AUTO
VDDIO - AUTO
VDDP - 0.95v

Memory Frequency: 6000Mhz

**Primaries**
TCL 30
TRCD 36
TRCD_WR 16
TRP 33
TRAS 126
TRC 64
TWR 48
TRFC 512
TRFC2 512
TRFCPB 412
TREFI 65535

**Secondaries**
TRRD_S 8
TRRD_L 8
TRTP 16
TFAW 32
TCWL 36
TWTR_S 4
TWTR_L 4

**Tertiaries**
TRDRDSCL 4
TRDRDSC 1
TWRWRSCL 4
TWRWRSC 1
TWRRD 4
TRDWR 16

**DRAM Training Configuration**
Round Trip Latency ENABLED

> **TEAMGROUP T-Create Expert Overclocking 10L DDR5 48GB Kit (2 x 24GB)...**
> https://www.amazon.co.uk/TEAMGROUP-T-Create-Overclocking-7200MHz-PC5-57600-Black-UDIMM/dp/B0C4NNRC56
> TEAMGROUP T-CREATE EXPERT Overclocking 10L DDR5 48GB Kit (2 x 24GB) 7200MHz (PC5-57600) CL34 M-DIE Desktop Memory Module Ram Black - CTCED548G7200HC34ADC01
