# Useful Registry Tweaks

*Category: Windows Tweaks | Originally posted: 2023-01-23 | 10 message(s)*

Here are some useful windows registry tweaks that make the operating system more convenient 😀

![Screenshot_2023-01-23_175534.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067140928353087508/Screenshot_2023-01-23_175534.png?ex=6a8b346f&is=6a89e2ef&hm=3917f15789e4a7990f4d136dc9a7356d742b587ca917cccfabbf31d00a372e58&)

---
**Raheem** (2023-01-23):

To carry out these tweaks you must have registry editor open. any registry paths that i put in here and be copied and pasted into the bar at the top to get there quicker

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067142143421976776/image.png?ex=6a8b3591&is=6a89e411&hm=99792de3e42f07d77909202da2ecd94fb0133c12317780080940060743c27df5&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067142143682019378/image.png?ex=6a8b3591&is=6a89e411&hm=f1e43effcbaa655fd12b8aea33f97c7e8480e60cd4ca319d5c83cb7e5ddd3608&)

---
**Raheem** (2023-01-23):

Disable Dynamic Search Box

HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\SearchSettings

Right Click > DWORD (32-bit) Value
name it EXACTLY 
IsDynamicSearchBoxEnabled

Set Value to 0
Press OK

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067143295060410448/image.png?ex=6a8b36a4&is=6a89e524&hm=7f84b8a941f77d0967dfdae06c76db8fc987a8b5bd82516bc067e78b7a36ce27&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067143295328866434/image.png?ex=6a8b36a4&is=6a89e524&hm=4537cdc3ecad169f5977c3fc4ceb0f53145cab2a057b12c8d88b5ea93ad6a038&)

---
**Raheem** (2023-01-23):

Remove Bing from Start

HKEY_CURRENT_USER\SOFTWARE\Policies\Microsoft\Windows

Right click Windows > New > Key

Name the key EXACTLY 
Explorer

Right click Explorer > DWORD (32-bit) Value > Name it EXACTLY
DisableSearchBoxSuggestions

Set Value to 1
Press OK

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067145152738639943/image.png?ex=6a8b385f&is=6a89e6df&hm=9c25c78cabf19183a055c200f5db84deb49b2a3c0daf7e21f377c569bb383131&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067145154185658368/image.png?ex=6a8b385f&is=6a89e6df&hm=8e509169423773d7caac883c05c92b9e3dd8b6d5987ede27fbe86f3c976e3d19&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067145154391199774/image.png?ex=6a8b385f&is=6a89e6df&hm=d1f54f95b67ddf0163c4295d5da3c5dfddf51bc3e8734dd8219eacfdf00b0eb0&)

---
**Raheem** (2023-01-23):

Bypass TPM and CPU checks for Windows Update

HKEY_LOCAL_MACHINE\SYSTEM\Setup\MoSetup

Right click > DWORD (32-bit) Value > Name it EXACTLY
AllowUpgradesWithUnsupportedTPMOrCPU

Set value to 1
Press OK

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067146417908482089/image.png?ex=6a8b398c&is=6a89e80c&hm=c4b027774fbde85664d66f69cf0148668d9d99939afcf143567c33f254d9ddde&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067146418143379578/image.png?ex=6a8b398c&is=6a89e80c&hm=659beae0407de9793e080f408216fd7ee03f7696b28f6144c76c7415d6aea1bd&)

---
**Raheem** (2023-01-23):

Restore Context Menu

HKEY_CURRENT_USER\SOFTWARE\CLASSES\CLSID\

Right click CLSID > Key > Name it EXACTLY
{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}

Right click {86ca1aa0-34aa-4e8b-a509-50c905bae2a2} > Key > Name it EXACTLY
InprocServer32

Go to InprocServer32 > Double Click (Default) and then leave the value data blank and PRESS OK

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067148246318850108/image.png?ex=6a8b3b40&is=6a89e9c0&hm=3f68bdd6423cce6714d88d7a83eefac06e58bdfd261296f60cd5be5f4e12c04b&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067148246637625455/image.png?ex=6a8b3b40&is=6a89e9c0&hm=f6249e4fcfc16c0f1e1672cdce42c3537c299541965f5d1be3f372e42214f46c&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067148247044464700/image.png?ex=6a8b3b40&is=6a89e9c0&hm=82cb0fd6d930c6dcbaaed5731a3c6a41e22c82912dda7cdffff869d2b400d4ae&)

---
**Raheem** (2023-01-23):

Disable Snap Layout

HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\

Right click > DWORD (32-bit) Value > Name it EXACTLY
EnableSnapAssistFlyout

Set value to 0
Press OK

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067149185796812810/image.png?ex=6a8b3c20&is=6a89eaa0&hm=c56207206bdf0b5560a857933c7a6eab69079b66f54e5b2c9909f82910c0bbe2&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067149186102992896/image.png?ex=6a8b3c20&is=6a89eaa0&hm=dfdd824e3e8014205ed5e52cc3df820a5e202bf8366d5d8ffdda2125ce6e9cf3&)

---
**Raheem** (2023-01-23):

Disable Lockscreen

HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\

Right click Windows > Key > Name it EXACTLY
Personalization

Right click > DWORD (32-bit) Value > Name it EXACTLY
NoLockScreen

Set value to 1
Press OK

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067150438266310686/image.png?ex=6a8b3d4b&is=6a89ebcb&hm=17a0516d6e4d066e2a02ba96937784f40d4086df03a647e3fd2abf42127239fe&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067150438501199912/image.png?ex=6a8b3d4b&is=6a89ebcb&hm=a57293967bd571aa715124e62a06eb294d140e7f100a00b0c6f67b2907a755ad&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067150438715105280/image.png?ex=6a8b3d4b&is=6a89ebcb&hm=bd823893b7706cd636c529a301c6b1c5a0c1546c2597add3f4590f8cf7ed6e5b&)

---
**Raheem** (2023-01-23):

Speed Up Shutdown

HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control

WaitToKillServiceTimeout

Set value to 500
Press OK

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1067151154980593784/image.png?ex=6a8b3df6&is=6a89ec76&hm=3c9002990bb141815add066d65e1b3d2e7e2c454ecebd9f9ad26bc2c45e7ff14&)

---
**Raheem** (2023-04-27):

Network Throttle and System Responsiveness

HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile

Double click on NetworkThrottlingIndex & set the value to "ffffffff" hexadecimal
Press OK

Double click on SystemResponsiveness & set the value to "0" hexadecimal
Press OK

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1101147766673129532/image.png?ex=6a8afec5&is=6a89ad45&hm=d079fafda47936000cfab0027a77b7d8551d5ce334ad47b3347de9ac4632580e&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1101147766912208997/image.png?ex=6a8afec5&is=6a89ad45&hm=5ff9fbf00aa4b15a2936779871544cacc44296ceca95f5fd26c43be3c9ce48db&)

![image.png](https://cdn.discordapp.com/attachments/1067140928214663259/1101147767193215017/image.png?ex=6a8afec6&is=6a89ad46&hm=1044c00fe3650fe7f86a33c087ebe84dc743be803a6ca66589640380356f161b&)
