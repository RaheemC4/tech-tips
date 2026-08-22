# Windows 11 Custom Image

*Category: Windows Tweaks | Originally posted: 2024-08-24 | 6 message(s)*

I have spent some time creating a custom windows 11 image that comes preconfigured with the tweaks in 𝗧𝗲𝗰𝗵-𝗧𝗶𝗽𝘀💡so that people don't have to do them every time they reinstall windows

The Windows 11 Custom Image Contains:

* Discord pre-installed
* Game launchers pre-installed
* Driver updater on the desktop
* Office 365 Pre-activated
* Windows 11 Pro Pre-activated
* 𝗧𝗲𝗰𝗵-𝗧𝗶𝗽𝘀💡 tweaks applied

The only thing that could not be prconfigured are the Driver installs. This is because it is user hardware dependent. So to prevent any driver conflict issues, you **MUST** run DriverBooster on the desktop when you install windows.

**DOWNLOAD LINK AT BOTTOM**

![Windows2011-011.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276952543943065743/Windows2011-011.png?ex=6a8b2a3b&is=6a89d8bb&hm=9bfc1e321c9b4de78958085048f92fdb7e43d177e3548b5b3fa8f3068a250ff4&)

---
**Raheem** (2024-08-24):

USB Setup Guide

This is a guide to putting the image on a USB.

First download the .iso from the link at the bottom of this post

Then download Rufus - https://github.com/pbatard/rufus/releases/download/v4.5/rufus-4.5.exe

Open Rufus, make sure your USB is at least 16GB and plugged into the PC

Select the USB from the device list. Click where it says SELECT next to Boot Selection and open the windows 11 custom image .iso file you downloaded from the link at the bottom of this post https://discord.com/channels/338387884539248640/1276952543791943750/1276972070915276801

for Volume label, pick whatever you want the USB to be named

Press Start and tick the bottom 2 boxes and press OK twice

Wait for Status at the bottom to say READY

Close

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276964008464879716/image.png?ex=6a8b34e8&is=6a89e368&hm=da008148e893a3819aa8a60bb57520cd7a155bf3eb67d33dcce4c6a970d48aaf&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276964008682852363/image.png?ex=6a8b34e8&is=6a89e368&hm=65113bb5717eeba223f54bac41ed462c7349ac425eadbd2407a9e50e17722b97&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276964008930578536/image.png?ex=6a8b34e8&is=6a89e368&hm=a62a0cdab9d862dc124ffae7b831cca83bb95c582dfeab3435b314ab2f9c054e&)

---
**Raheem** (2024-08-24):

Install Onto Drive

Boot into the USB through BIOS

Click the windows icon at the bottom and choose Setup [OLD VERSION]

Leave Language to install as US
Change The bottom 2 options to United Kingdom
Press Next

Tick the box and press Next

Custom: Install Windows only (Advanced) 

Make sure you know which drive is the one you want to install windows on.
If you have multiple drives, you can identify which partition belongs to which drive as for example it will have Drive 0 and Drive 1 to identify the first and second drives. I want to install Windows on my first drive which for me is Drive 0 so I select every single partition for Drive 0 and press Delete so that all the partitions merge into 1 unallocated space and windows installs on the entire drive and not just a single partition.

Select the drive that you have deleted all the partitions for and press Next

Wait for the install process to finish and it will automatically restart the machine

Once the machine has started to restart either unplug your USB or go into BIOS and boot the drive that you have installed windows on so that it doesnt boot back into the USB.

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276966854648266762/image.png?ex=6a8b378f&is=6a89e60f&hm=08a2ed4c4c92ae2ad3364848350068cb8a84011637da223c96669c0fcc4414cf&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276966854979751976/image.png?ex=6a8b378f&is=6a89e60f&hm=35c0e64fe866bac6129f0b909ef941a65463f5450b7ee1a52c45835d5d1e248c&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276966855306903572/image.png?ex=6a8b378f&is=6a89e60f&hm=082dcc4912742960dd93cf5959e7030a0ec2cad96d15c2043a2d9070186cfe1d&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276966855663161384/image.png?ex=6a8b378f&is=6a89e60f&hm=c2fb211d3d2a62f4196bc2d6687aae51319ff6efbd7ebd099c4ed9ebb744f74a&)

---
**Raheem** (2024-08-24):

Windows 11 Setup

Choose United Kingdom for the first 2 pages

Skip adding a second keyboard layout

You can choose to name your PC or Skip

When it gets to the  'How would you like to setup this device?' 
We need to use cmd to disconnect from the network so that we can bypass it asking us to sign in with a microsoft account.
Press **Shift + F10** to open CMD
type **ipconfig/release**
Close CMD and press 'Setup for Personal Use'

Choose a name for the account of the PC
Next

You **do not need** to enter a password
Next

For the remaining pages, keep choosing the bottom option and pressing next until it takes you to the desktop

Once you are on the desktop, you need to enable connection to the network again.
Open CMD
Typ **ipconfig/renew**
Close CMD

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276969515208544397/image.png?ex=6a8b3a09&is=6a89e889&hm=7a0052262d3a5e5a566a9903b55c474276fe55b8cf2ec60dd19f134e60f40450&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276969515586027630/image.png?ex=6a8b3a09&is=6a89e889&hm=ac890212447320ac4794fe881ad2f7d9907fde95a6dcc79d2890aa64cb4ec656&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276969515993006100/image.png?ex=6a8b3a09&is=6a89e889&hm=b6fcdb1ea71a58c5f6089bcc104c30ac0e44e786c9412d6efcfdc588437e1a7b&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276969516341002302/image.png?ex=6a8b3a09&is=6a89e889&hm=f1eb31cbee6e19c558e36e3be1d7dc51c7b510aeef6982b5bb4ac2651b1aab6c&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276969516613763133/image.png?ex=6a8b3a09&is=6a89e889&hm=f8a8cc6046d12ad08422965962d55a9cbad8205af3edbe11957ad3c08a7a516a&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276969643596058708/image.png?ex=6a8b3a27&is=6a89e8a7&hm=4e49ccd138229af1e59a7d4d59f6487529276649aa8e03e7d9ccba9e5a29d2a5&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276969643977871370/image.png?ex=6a8b3a28&is=6a89e8a8&hm=782a84d47bfb36a8f9da5635469fcf1d6dbf4f0d4db14cad5f96ace154c5b299&)

---
**Raheem** (2024-08-24):

REQUIRED DRIVERS INSTALL

Open Driver Booster on the desktop

SCAN

Tick Outdated box
Untick any NVIDIA Graphics Card Drivers (Use NVCleanstall for those)
Update Now

Once it has finished downloading and installing the drivers
Reboot

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276971682145239041/image.png?ex=6a8b3c0e&is=6a89ea8e&hm=f5c5660ab4a85eae3bfb498d036fd85b3e119eaafd2d1d4df7f4df7fc14df360&)

![image.png](https://cdn.discordapp.com/attachments/1276952543791943750/1276971682476720219/image.png?ex=6a8b3c0e&is=6a89ea8e&hm=e7d0516e491984d30d55a4b9d0bb816097b34fa603babad09bd08a0c0354b1da&)

---
**Raheem** (2024-08-24):

WINDOWS 11 .iso LINK

https://drive.proton.me/urls/87FREE2SZM#P8y0Bc1mlWIk

> **Proton Drive**
> https://drive.proton.me/urls/87FREE2SZM
> Securely store, share, and access your important files and photos. Anytime, anywhere.
