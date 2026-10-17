"""Explicit snapshots for tweak settings outside the registry.

All scripts and command names are owned by the app. Captured strings are quoted
as PowerShell literals; no persisted or renderer-supplied scripts are executed.
"""
import json
import re


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def checked(args):
    import tweaks_engine as engine
    code, output = engine.run(args)
    if code:
        raise OSError(output.strip() or 'Windows command failed.')
    return output


def ps_checked(script):
    import tweaks_engine as engine
    code, output = engine.ps("$ErrorActionPreference='Stop'; " + script)
    if code:
        raise OSError(output.strip() or 'Windows setting could not be read or written.')
    return output


def json_state(query, restore_script):
    def read():
        text = ps_checked('ConvertTo-Json -InputObject @(' + query + ') -Depth 5 -Compress')
        result = json.loads(text)
        if not isinstance(result, list):
            raise ValueError('Windows returned an invalid settings snapshot.')
        return result
    original = read()
    scripts = [restore_script(row) for row in original]
    def restore():
        for script in scripts:
            ps_checked(script)
        if read() != original:
            raise OSError('The original setting did not read back after restore.')
    return restore


def capture_external(key):
    if key == 'ultimate_power':
        def read():
            output = checked(['powercfg', '/getactivescheme'])
            match = re.search(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', output)
            if not match:
                raise ValueError('Could not capture the active power plan.')
            return match[0].lower()
        original = read()
        def restore():
            checked(['powercfg', '/setactive', original])
            if read() != original:
                raise OSError('The original power plan did not become active.')
        return restore
    if key == 'dynamic_tick':
        def read():
            output = checked(['bcdedit', '/enum', '{current}'])
            for line in output.splitlines():
                parts = line.split()
                if parts and parts[0].lower() == 'disabledynamictick':
                    if len(parts) != 2 or parts[1].lower() not in ('yes', 'no'):
                        raise ValueError('Could not capture the boot timer flag.')
                    return parts[1].lower()
            return None
        original = read()
        def restore():
            if read() != original:
                checked(['bcdedit', '/deletevalue', '{current}', 'disabledynamictick'] if original is None
                        else ['bcdedit', '/set', '{current}', 'disabledynamictick', original])
            if read() != original:
                raise OSError('The original boot timer flag did not read back.')
        return restore
    if key in ('mem_compression', 'page_combining'):
        flag = {'mem_compression':'MemoryCompression', 'page_combining':'PageCombining'}[key]
        return json_state(f'Get-MMAgent | Select-Object {flag}',
                          lambda row: ('Enable' if row[flag] else 'Disable') + '-MMAgent -' + flag)
    if key in ('sysmain', 'diagtrack'):
        name = {'sysmain':'SysMain', 'diagtrack':'DiagTrack'}[key]
        def restore_service(row):
            status = row['Status']
            if status not in ('Running', 'Stopped', 'Paused'):
                raise ValueError('Service is transitioning; wait before restoring it.')
            name_literal = quote(row['Name'])
            if status == 'Stopped':
                return 'Stop-Service -Name ' + name_literal
            command = '$s=Get-Service -Name ' + name_literal + '; if($s.Status -eq "Paused"){Resume-Service -Name ' + name_literal + '}else{Start-Service -Name ' + name_literal + '}'
            if status == 'Paused':
                command += '; Suspend-Service -Name ' + name_literal
            return command
        return json_state(f'Get-Service -Name {quote(name)} | Select-Object Name,@{{n="Status";e={{[string]$_.Status}}}}', restore_service)
    if key == 'firewall_notify':
        return json_state('Get-NetFirewallProfile -All | Sort-Object Name | Select-Object Name,@{n="Notify";e={[string]$_.NotifyOnListen}}',
                          lambda row: 'Set-NetFirewallProfile -Name ' + quote(row['Name']) + ' -NotifyOnListen ' + quote(row['Notify']))
    if key == 'nic_offload':
        fields = ('Chimney', 'ReceiveSegmentCoalescing', 'PacketCoalescingFilter')
        query = 'Get-NetOffloadGlobalSetting | Select-Object ' + ','.join('@{n="'+f+'";e={[string]$_.'+f+'}}' for f in fields)
        return json_state(query, lambda row: 'Set-NetOffloadGlobalSetting ' + ' '.join('-'+f+' '+quote(row[f]) for f in fields if row[f]))
    if key == 'usb_power_mgmt':
        query = '$ids=@((Get-CimInstance Win32_USBHub).PNPDeviceID); Get-CimInstance -ClassName MSPower_DeviceEnable -Namespace root/wmi | Where-Object {$instance=$_.InstanceName; @($ids | Where-Object {$instance -like ($_ + "*")}).Count -gt 0} | Sort-Object InstanceName | Select-Object InstanceName,Enable'
        return json_state(query, lambda row: 'Get-CimInstance -ClassName MSPower_DeviceEnable -Namespace root/wmi | Where-Object InstanceName -eq ' + quote(row['InstanceName']) + ' | Set-CimInstance -Property @{Enable=$' + str(row['Enable']).lower() + '}')
    if key == 'nv_telemetry':
        import tweaks_engine as engine
        patterns = ','.join(quote(x) for x in engine.NV_TASK_PATTERNS)
        query = f'Get-ScheduledTask | Where-Object {{$name=$_.TaskName; @(@({patterns}) | Where-Object {{$name -like $_}}).Count -gt 0}} | Sort-Object TaskPath,TaskName | Select-Object TaskPath,TaskName,@{{n="Enabled";e={{[bool]$_.Settings.Enabled}}}}'
        return json_state(query, lambda row: ('Enable' if row['Enabled'] else 'Disable') + '-ScheduledTask -TaskPath ' + quote(row['TaskPath']) + ' -TaskName ' + quote(row['TaskName']) + ' | Out-Null')
    # Other tweak definitions change only registry values, captured by the engine.
    return lambda: None
