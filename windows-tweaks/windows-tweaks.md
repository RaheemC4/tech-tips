# Windows Tweaks

*Category: Windows Tweaks | Originally posted: 2022-09-16 | 17 message(s)*

Registry Tweaks

An essential thing u must do for better performance is disable GameDVR in windows via the registry.if u want to press Windows+R to open the run box, then u want to type in regedit and press enter


You then want to head over to this path 

Computer\HKEY_CURRENT_USER\System\GameConfigStore



Double click GameDVR_Enabled and set the value to 0
`

You then want to head over to this path 
Computer\HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\PolicyManager\default\ApplicationManagement\AllowGameDVR

change ***value*** to 0

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020257311199076362/unknown.png?ex=6a8ab62a&is=6a8964aa&hm=0076d354d8cf122f69814e5f8c97c89234d4b7ccbadfb391ad4287f97ffec62d&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020257311547211806/unknown.png?ex=6a8ab62a&is=6a8964aa&hm=8582c0a0dea778604cf47894802434c7a9ba2e389dd95cd758f1a02d14abd77d&)

---
**Raheem** (2022-09-16):

Background Apps

Turning off background apps in windows settings can reduce cpu and ram usage helping out with performance. go to windows settings (Windows+i) and type background apps in search, then toggle it off

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020257538236751924/unknown.png?ex=6a8ab660&is=6a8964e0&hm=78dba51504814873d060c278bedaa1551ebc486af23314cbe07d0089c39dbef4&)

---
**Raheem** (2022-09-16):

Task Manager
Startup Apps

if u open task manager (Ctrl+Shift+Escape) u can make ur pc boot into windows faster by going to the startup tab and disabling the apps u dont need starting straight away. leaving discord on is preferred but pretty much anything else can be turned off.

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020257754457329684/unknown.png?ex=6a8ab694&is=6a896514&hm=675f19ae0e6fd394b62e9712a1b599b5611a09d463f077ff36e470c6420876d2&)

---
**Raheem** (2022-09-16):

Mouse

always make sure u guys disable mouse acceleration in windows. it makes ur aim better. u can do this by pressing windows and searching mouse. go to mouse settings, go to additional mouse options, go to pointer options and untick enhance pointer precision.

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020260604004540488/unknown.png?ex=6a8ab93b&is=6a8967bb&hm=912748cc4a37bd68a7fbbedc039738c685cf8ba82dde019b96693342967568e0&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020260604352680016/unknown.png?ex=6a8ab93b&is=6a8967bb&hm=7fe5848bae8c039ba4603f244554a6df75cb94e0665b8896ac2f742aea439729&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020260604650459186/unknown.png?ex=6a8ab93b&is=6a8967bb&hm=cf4ca78a5f398985aa4dd9e738950f769adb6652162b354bffc6e269dfae92ee&)

---
**Raheem** (2022-09-16):

MOUSE ACCELERATION FIX 


Mouse Acceleration can be enabled by SOME GAMES without your approval. there have been some games that will either do that or ignore your preferences for Hardware Cursor and force a Software Cursor. there are versions for DPI/Windows scaling at 100,125,150,200%. 

 
https://onedrive.live.com/download?cid=0396A2F7CEB35712&resid=396A2F7CEB35712%21884&authkey=AH8a0AvcDqeTdzM


Download the file -> Extract Zip -> Go to 'Windows 10 Fixes' -> and run the .reg file that has your zoom level in windows display settings eg 100% 125% -> Restart to apply the fix.

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020266219921752064/unknown.png?ex=6a8abe76&is=6a896cf6&hm=497c336bfd46fc9175537942bc1935c9eff30f23d21778a3e828d6df8a4dd8d9&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020266220295036938/unknown.png?ex=6a8abe76&is=6a896cf6&hm=8da53e51c35d0a87b227b6785b9c91b03f46110a6b808df17f103ca945d30624&)

---
**Raheem** (2022-09-16):

WINRAR KEY

Put this in C:\Program Files\WinRAR to stop it from asking for you to buy a key

[rarreg.key](https://cdn.discordapp.com/attachments/1020257311069065226/1020267001425432596/rarreg.key?ex=6a8abf30&is=6a896db0&hm=b719ef9ebb44994b7d445a2dbe82ff553572daaa8830453de0c241d5390f690f&)

---
**Raheem** (2022-09-16):

OPTIMISERS and FPS BOOST VIDEOS


 If u find any fps boost videos online where they install latency optimisers such as intelligent standby list cleaner, change the timer resolution or park the cores of the cpu DO NOT DO IT. it will actually decrease fps in games due to the cpu/RAM having to run more processes in the background, which u are trying to minimise to increase fps in games. DO NOT WATCH PANJNO VIDEOS, THEY ARE CLICKBAIT AND FAKE. HE POSTS THE SAME VIDEO EVERY TIME ONLY CHANGING A FEW THINGS. 
 **https://youtu.be/Li6S033oHug?t=972**

> **FPS BOOSTING apps WORK??**
> https://www.youtube.com/watch?v=Li6S033oHug
> RESULTS!! - Testing the most common FPS boosting APPS

---
**Raheem** (2022-09-16):

NETWORK ADAPTER SETTINGS


To make ur network better on pc, follow these steps (if using ethernet). Right click ur ethernet icon and press open network and internet settings



 then select network and sharing center



Select Ethernet



Press Properties



Select Configure



go to power management and untick both these boxes



Go to the advanced tab and disable anything that has the word Offload in it or any power saving/green options



Disable anything that i have highlighted in yellow



If you have a cat 5+ ethernet cable with ur ethernet drivers updated, set ur speed and duplex to 1.0gb or 2.5gb full 
then press OK

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020270056145428510/unknown.png?ex=6a8ac209&is=6a897089&hm=3fc47e1f0a58051bed948d07c0a9d85e2621f5afd79a9613886c4814f5096c90&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020270056552267806/unknown.png?ex=6a8ac209&is=6a897089&hm=1d14e6d77dbfe78ea99b96739ae260edaeed339672e3356bebc745744c591400&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020270056938147860/unknown.png?ex=6a8ac209&is=6a897089&hm=65f114280f7d8bd4011802e1248a4f096946f455dc65fa5b3c057e1061c6f343&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020270057676349550/unknown.png?ex=6a8ac209&is=6a897089&hm=d72a6931ce7aa28027997d1280cd5a8e53312918a91afcb803a1438037183586&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020270058053840896/unknown.png?ex=6a8ac209&is=6a897089&hm=459660943ab462d3a8cc66becf6bf1746dd783bfb86d00ea8a7faaf974dee0c4&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020270058439720961/unknown.png?ex=6a8ac209&is=6a897089&hm=a1470dc4fc0050b84b5f53adf6dabe03fcc0532b2cdd5f09ce5e7965a22d264e&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020270058745896960/unknown.png?ex=6a8ac209&is=6a897089&hm=1ab9c8740ed929b5f4d4e0f8750dc3266290049793a7552053a8fcfca884b1f1&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020270059148554240/unknown.png?ex=6a8ac209&is=6a897089&hm=9d9a310203cfd8aacfc35bc97fa082c814ed541a30f6d5cd79537a5a77b25ae5&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020270059479896094/unknown.png?ex=6a8ac209&is=6a897089&hm=cadde5f0e6b4e4010c3f3f5304cef798325e6aa4226d52c14c243d97a8d9ff59&)

---
**Raheem** (2022-09-16):

Windows> Network & Internet 

>advanced network settings> 

More network adapter options>

right click your adapter and hit properties 

uncheck ALL but these

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1020270292066631710/unknown.png?ex=6a8ac241&is=6a8970c1&hm=6f4bfe2a97224a8fae95bcac3aaae213d82a7b616524d843c56b298ee40533b7&)

---
**Raheem** (2022-10-22):

DEVICE MANAGER USB SETTINGS


windows will automatically put power management mode on pretty much anything it can, this is true for the USB ports too. i found that i had issues with my keyboard not waking on startup due to this so i managed to find a solution for it via device manager.



To do this, open DEVICE MANAGER by searching for it in the windows search bar, then scroll down to UNIVERSAL SERIAL BUS CONTROLLERS and open the sub menu by pressing the arrow icon beside the name. you then double click all the devices in the sub menu, head to the POWER MANAGEMENT tab and untick the 'Allow the computer to turn off this device to save power'. I have found that this can be done for all the 'USB Hubs' and 'Mass Storage Devices' but the 'USB Composite Devices' do not have the POWER MANAGEMENT tab so you can skip them.

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1033423618308329492/unknown.png?ex=6a8b263e&is=6a89d4be&hm=3131cec9b2b9914d737121b0ef3b733c401b237f70c3342be62edd81f1f8bcaf&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1033423618836791426/unknown.png?ex=6a8b263e&is=6a89d4be&hm=6712bbb60c9024e89d1e5562a89808a3418fed5b47f1e435cabccd372e9067d4&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1033423619428192396/unknown.png?ex=6a8b263e&is=6a89d4be&hm=857ad517c143a92a8a1b27e0d4675adbdfee29029d44f80cb3cbc88c04dac027&)

---
**Raheem** (2022-10-29):

INTERNET OPTIONS



windows has a bunch of stuff that dont need to be on that just is, this is one of them. normally when u download something and run it, it will ask if you are sure you wanna run it. this makes it not ask that every time.



Press windows and type Internet Options, then go to the security tab and drag the slider for security level to medium. then press custom level, and scroll down to 'Launching applications and unsafe files (not secure)' and tick ENABLE . then press OK

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1035739028684808222/unknown.png?ex=6a8b00e3&is=6a89af63&hm=27629c3cdec7cdccb8c62bb17378836bc45237b1e6a249a4a364e4d98bcb62dd&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1035739029091659896/unknown.png?ex=6a8b00e3&is=6a89af63&hm=547468aec579154d6c685c75da3a238c9cbddcb78d9595bb06f32f0b82c49c98&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1035739029464948807/unknown.png?ex=6a8b00e3&is=6a89af63&hm=06dd4e930461af8d5adcb74dc5e767bff4d15c12b6e5777add8c05581f8fe5c3&)

---
**Raheem** (2022-10-29):

FIREWALL NOTIFICATIONS


Sometimes when you run a new application or game for the first time it prompts you for firewall whether you want to allow it or not. this should stop it from asking that



Press windows and type firewall and open 'Windows Defender Firewall'. then open 'Change notification settings' and untick 'Notify me when Windows Defender Firewall blocks a new app'. press OK

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1035740031387709470/unknown.png?ex=6a8b01d2&is=6a89b052&hm=e65afa9f2b4d859eb6c3b5d2e4fc7deb7708eb0831dc495cc0a9b8d48da54789&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1035740031719051264/unknown.png?ex=6a8b01d2&is=6a89b052&hm=8b49579acfecfa6b7406810ec30f690b01c5177908457c880110d16aa2928592&)

![unknown.png](https://cdn.discordapp.com/attachments/1020257311069065226/1035740032121708554/unknown.png?ex=6a8b01d2&is=6a89b052&hm=105b44ee1001b39349466f5f5b95cec05210aca2f0e7d195f942adcdbe85a62f&)

---
**Raheem** (2023-02-12):

System Restore Points


By default on some systems, windows does not enable auto system restore points. Restore points are very important for windows computers as it allows you to rollback your pc to a specific state. This can be useful if you have any windows file corruptions or viruses that you want to clear, you can just rollback to a previous state closest to the present day and your all gucci



TO ENABLE SYSTEM RESTORE POINTS:

Search for Restore in windows 
and open Create a restore point

Check if your system drive has protection set to ON

If not, select the system drive, press configure, set system protection to ON and set Max Usage to 2%
Press OK

After that just go ahead and press create so that you can create a restore point of your current state manually
Press OK

![image.png](https://cdn.discordapp.com/attachments/1020257311069065226/1074123912851492864/image.png?ex=6a8ae699&is=6a899519&hm=f48e5c43e72dc0660b2c517161ce861410630680904d00c1107d6a5a03f07de6&)

![image.png](https://cdn.discordapp.com/attachments/1020257311069065226/1074123913040232601/image.png?ex=6a8ae699&is=6a899519&hm=2f9f3d528047c578bc369d37905f7dd0d0235309f98a8ad31fe0e2f868b64ea6&)

![image.png](https://cdn.discordapp.com/attachments/1020257311069065226/1074123913220595723/image.png?ex=6a8ae699&is=6a899519&hm=3a5580c6d61f95db3601d3b8da33aaf8afd90ecfc63472882dde079b548b6fcc&)

---
**Raheem** (2023-03-15):

GPU MSI UTILITY 



Open MSI_util_v3.exe as an administrator

Find your Graphics Card, Tick msi

Change Interrupt Priority to High 

Apply

[MSI_util_v3.exe](https://cdn.discordapp.com/attachments/1020257311069065226/1085366970842619915/MSI_util_v3.exe?ex=6a8aef02&is=6a899d82&hm=fe074fa468c8fb6d54e6b4738fa901de9f0021e2588a1a20abd9f84c265faf68&)

[20230315-0100-13.2635244.mp4](https://cdn.discordapp.com/attachments/1020257311069065226/1085366971383676998/20230315-0100-13.2635244.mp4?ex=6a8aef03&is=6a899d83&hm=042bc620e6ecec78a5843b114665b27b07b67832fa39bb80c276d94276f3751b&)

---
**Raheem** (2023-04-27):

Adjusting Timer Resolution



Open Device Manager & Expand System Devices
Find 'High Precision Event Timer' and then disable it
Open Powershell as an administrator
Copy and paste these 1 at a time and press enter:

bcdedit /set useplatformclock no

bcdedit /set useplatformtick yes

bcdedit /set disabledynamictick yes

Restart PC

Done

[Adjusting_Timer_Resolution.mp4](https://cdn.discordapp.com/attachments/1020257311069065226/1101145475073187860/Adjusting_Timer_Resolution.mp4?ex=6a8afca3&is=6a89ab23&hm=fc5b2c8e5eafca63a340b8467e95a2f05fd11fdecb608cd356a4279ebfc00993&)

---
**Raheem** (2023-04-27):

Networking Tweak - Powershell



Open Powershell as an administrator

Copy and paste these 1 at a time and press enter:

Set-NetOffloadGlobalSetting -Chimney Disabled

Set-NetOffloadGlobalSetting -ReceiveSegmentCoalescing disabled

Set-NetOffloadGlobalSetting -PacketCoalescingFilter disabled

Restart PC

Done

[Networking_Tweak_Powershell.mp4](https://cdn.discordapp.com/attachments/1020257311069065226/1101146372935274537/Networking_Tweak_Powershell.mp4?ex=6a8afd79&is=6a89abf9&hm=c30c1f4148d5ec9dcdfc804579eada9401355520a8eb33d3f19095b81bf4a5f3&)

---
**Raheem** (2023-05-22):

Power Options tweak - lower chipset temperature


Open power plan options
Expand PCI Express
Expand Link State Power Management
Set Setting: Maximum Power Savings

This is a weird solution to help drop chipset temperature in windows but it has little to no effect on performance

![image.png](https://cdn.discordapp.com/attachments/1020257311069065226/1110327611609071727/image.png?ex=6a8ac5eb&is=6a89746b&hm=5c1a7880987b718247b63b94658c64ad0eab64cb82ea4e533e0ab16a0adb208e&)

[20230522-2204-15.5975050.mp4](https://cdn.discordapp.com/attachments/1020257311069065226/1110327612007534712/20230522-2204-15.5975050.mp4?ex=6a8ac5eb&is=6a89746b&hm=39ae863ca33a89efa091bbe3e65a0d3091ad2d8c075881665ba04c2c4626c404&)
