"""Build the curated catalog from the pinned Win11Debloat metadata."""
import json
from pathlib import Path

src = Path(__file__).resolve().parents[1] / 'src'
vendor = src / 'vendor/win11debloat'
features = {x['FeatureId']: x for x in json.loads((vendor / 'Config/Features.json').read_text(encoding='utf-8-sig'))['Features']}
custom = ['ShowKnownFileExt', 'HideHome', 'TaskbarAlignLeft', 'HideSearchTb',
          'EnableDarkMode', 'HideDesktopSpotlightIcon', 'StartAllAppsList',
          'DisableStartRecommended', 'HideTaskview', 'EnableEndTask', 'ShowHiddenFolders']
debloat = ['DisableEdgeAds', 'DisableLockscreenTips', 'DisableSettings365Ads', 'DisableCopilot',
           'DisableRecall', 'DisableClickToDo', 'DisablePaintAI', 'DisableNotepadAI', 'DisableEdgeAI']
optional = ['HideGallery', 'HideDupliDrive']
items = []
for key in custom + debloat + optional:
    f = features[key]
    items.append(dict(id=key, title=f['Label'], description=f.get('ToolTip', f['ApplyText']),
                      group='Debloat' if key in debloat else 'Customization',
                      recommended=key not in optional, kind='registry',
                      registry=f['RegistryKey'], undo=f['RegistryUndoKey'],
                      min_build=f.get('MinVersion') or 22000))
items += [dict(id='ShowSecondsClock', title='Show seconds in the taskbar clock',
               description='Show hours, minutes and seconds. May use slightly more power.',
               group='Customization', recommended=True, kind='registry', min_build=22631,
               registry='../../../debloat-reg/ShowSeconds.reg', undo='../../../debloat-reg/HideSeconds.reg'),
          dict(id='ClearStartOnce', title='Clear pinned Start apps once for all users',
               description='Clear the current pinned list for existing profiles once. You can pin apps afterwards; later Recommended runs keep those pins. Existing layouts are backed up beside start2.bin.',
               group='Customization', recommended=True, kind='pins', min_build=22621)]
apps = {key: x for x in json.loads((vendor / 'Config/Apps.json').read_text(encoding='utf-8-sig'))['Apps']
        for key in ([x['AppId']] if isinstance(x['AppId'], str) else x['AppId'])}
for app in ['Clipchamp.Clipchamp', 'Microsoft.549981C3F5F10', 'Microsoft.BingFinance',
            'Microsoft.BingNews', 'Microsoft.BingSports', 'Microsoft.BingWeather',
            'Microsoft.Getstarted', 'Microsoft.MicrosoftOfficeHub', 'Microsoft.MixedReality.Portal',
            'Microsoft.SkypeApp', 'Microsoft.Copilot']:
    f = apps.get(app) or dict(FriendlyName='packaged Microsoft Copilot', Description='The Microsoft.Copilot Appx package, if installed')
    items.append(dict(id='app:' + app, title='Remove ' + f['FriendlyName'],
                      description=f['Description'] + '. Removes this app for all users and from provisioning; reinstall from Microsoft Store if wanted.',
                      group='Optional apps', recommended=True, kind='app', package=app, min_build=22000))
for item in items:
    if item['id'] == 'DisableStartRecommended':
        item['description'] += ' Windows edition and Start-menu rollout can affect whether the section disappears; a stored policy is not proof of the visual result.'
    if item['id'] == 'StartAllAppsList':
        item['description'] += ' Requires the newer Windows 11 Start menu (build 26200+).'
data = dict(upstream='32024662f3c602442e7af82bbf52c89143b31aeb', items=items,
            existing_recommended=['bing_search', 'cdm_ads', 'telemetry', 'ceip', 'feedback',
                                  'activity_history', 'ad_id', 'typing_insights', 'speech_data', 'ink_collection'])
(src / 'debloat_catalog.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
