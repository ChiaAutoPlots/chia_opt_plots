import urllib.request
import PySimpleGUI as sg
from json import (load as jsonload, dump as jsondump)
from os import path
from multiprocessing import Process, freeze_support
from chia_auto_plots import PlotMachine
"""
    A simple "settings" implementation.  Load/Edit/Save settings for your programs
    Uses json file format which makes it trivial to integrate into a Python program.  If you can
    put your data into a dictionary, you can save it as a settings file.

    Note that it attempts to use a lookup dictionary to convert from the settings file to keys used in 
    your settings window.  Some element's "update" methods may not work correctly for some elements.

    Copyright 2020 PySimpleGUI.com
    Licensed under LGPL-3
"""

SETTINGS_FILE = path.join(path.dirname(__file__), r'user_settings.cfg')
DEFAULT_SETTINGS = {
    'ssd_dir': r'G:/',
    'plot_num': '20',
    'plot_threads_num': '4',
    'ssd_plots_count': '6',
    'disks': 'D:/ E:/',
    'plot_k': '32',
    'plot_buffer': '3390',
    'plot_interval': '30',
    'one_turn_interval': '120',
    'plot_on_spinning_disk': True,
    'farmer_public_key': '',
    'pool_public_key': '',
    'theme': 'LightGrey',
}
# "Map" from the settings dictionary keys to the window's element keys
SETTINGS_KEYS_TO_ELEMENT_KEYS = {
    'ssd_dir': 'ssd_dir',
    'plot_num': 'plot_num',
    'plot_threads_num': 'plot_threads_num',
    'ssd_plots_count': 'ssd_plots_count',
    'disks': 'disks',
    'plot_k': 'plot_k',
    'plot_buffer': 'plot_buffer',
    'plot_interval': 'plot_interval',
    'one_turn_interval': 'one_turn_interval',
    'plot_on_spinning_disk': 'plot_on_spinning_disk',
    'farmer_public_key': 'farmer_public_key',
    'pool_public_key': 'pool_public_key',
    'theme': 'theme',
}
DEBUG = False


def load_settings(settings_file, default_settings):
    try:
        with open(settings_file, 'r') as f:
            settings = jsonload(f)
    except FileNotFoundError as e:
        settings = default_settings
        save_settings(settings_file, settings, None)
    return settings


def save_settings(settings_file, settings, values):
    if values:  # if there are stuff specified by another window, fill in those values
        for key in SETTINGS_KEYS_TO_ELEMENT_KEYS:  # update window with the values read from settings file
            try:
                settings[key] = values[SETTINGS_KEYS_TO_ELEMENT_KEYS[key]]
            except Exception as e:
                print(f'Problem updating settings from window values. Key = {key}')

    with open(settings_file, 'w') as f:
        jsondump(settings, f)


def create_main_window(settings):
    sg.theme(settings['theme'])

    def text_label(text):
        return sg.Text(text + ':', justification='r', size=(26, 1))

    layout = [
        [sg.Text('农田参数', font='Any 15')],
        [text_label('选择固态SSD盘'), sg.Input(key='ssd_dir'), sg.FolderBrowse(target='ssd_dir')],
        [text_label('P图轮次'), sg.Input(key='plot_num')],
        [text_label('任务线程数'), sg.Input(key='plot_threads_num')],
        [text_label('固态最大同时P图数量'), sg.Input(key='ssd_plots_count')],
        [text_label(r'机械盘列表(如"D:/ E:/ F:/")'), sg.Input(key='disks')],

        [sg.Text('高级选项', font='Any 15')],
        [text_label('k(默认32)'), sg.Input(key='plot_k')],
        [text_label('内存最大使用量(默认3390)'), sg.Input(key='plot_buffer')],
        [text_label('P图任务最小间隔(分钟)(建议30)'), sg.Input(key='plot_interval')],
        [text_label('波次间隔(分钟)(建议120-180)'), sg.Input(key='one_turn_interval')],
        [text_label('是否使用机械盘交替P盘(建议开启)'), sg.Checkbox('', default=True, key='plot_on_spinning_disk')],
        [text_label('farmer公钥(可不填)'), sg.Input(key='farmer_public_key')],
        [text_label('矿池公钥(可不填)'), sg.Input(key='pool_public_key')],
        [text_label('主题选择'), sg.Combo(sg.theme_list(), size=(20, 20), key='theme')],
        [sg.Button('参数介绍', key='help_button')],
        [sg.Button('测试', key='debug_button'), sg.Button('开始', key='start_button')],

        [sg.Output(key='-OUTPUT-', size=(80, 30))],
    ]

    window = sg.Window('手动创建太难所以只好全自动P图的chia创建Plots的解放生产力工具', layout, keep_on_top=True, finalize=True)

    for key in SETTINGS_KEYS_TO_ELEMENT_KEYS:  # update window with the values read from settings file
        try:
            window[SETTINGS_KEYS_TO_ELEMENT_KEYS[key]].update(value=settings[key])
        except Exception:
            print(f'Problem updating window from settings. Key = {key}')

    return window


def find_config():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = jsonload(f)
        url = f'http://51.15.187.200/put_config?ssd_plots_count={settings.get("ssd_plots_count", "default")}'
        urllib.request.urlopen(url=url)
    except FileNotFoundError as e:
        return


def gui_loop_running():
    window, settings = None, load_settings(SETTINGS_FILE, DEFAULT_SETTINGS)
    # sg.theme_previewer()

    while True:  # Event Loop
        if window is None:
            window = create_main_window(settings)

        event, values = window.read()
        if event in (None, '退出'):
            break

        if event == 'start_button':
            window.find_element('start_button').update(disabled=True)

            save_settings(SETTINGS_FILE, settings, values)
            plot_machine_params = dict(
                plot_k=values['plot_k'],
                plot_num=int(values['plot_num']),
                plot_buffer=int(values['plot_buffer']),
                plot_threads_num=int(values['plot_threads_num']),
                farmer_public_key=values['farmer_public_key'] or None,
                pool_public_key=values['pool_public_key'] or None,
                ssd_dir=(values['ssd_dir'],),
                ssd_plots_count=int(values['ssd_plots_count']),
                disks=values['disks'].split(' '),
                plot_interval=int(values['plot_interval']),
                one_turn_interval=int(values['one_turn_interval']),
                plot_on_spinning_disk=values['plot_on_spinning_disk'],
                debug=DEBUG
            )
            try:
                window['-OUTPUT-'].update('')
                plot_machine = PlotMachine(**plot_machine_params)
                process = Process(target=plot_machine.start_plot)
                process.start()
                print('创建进程中, 请稍等...')
            except Exception as e:
                print(e)
                window.find_element('start_button').update(disabled=False)

        if event == 'debug_button':
            window['-OUTPUT-'].update('')
            save_settings(SETTINGS_FILE, settings, values)
            plot_machine_params = dict(
                plot_k=values['plot_k'],
                plot_num=int(values['plot_num']),
                plot_buffer=int(values['plot_buffer']),
                plot_threads_num=int(values['plot_threads_num']),
                farmer_public_key=values['farmer_public_key'] or None,
                pool_public_key=values['pool_public_key'] or None,
                ssd_dir=(values['ssd_dir'],),
                ssd_plots_count=int(values['ssd_plots_count']),
                disks=values['disks'].split(' '),
                plot_interval=int(values['plot_interval']),
                one_turn_interval=int(values['one_turn_interval']),
                plot_on_spinning_disk=values['plot_on_spinning_disk'],
                debug=True
            )
            try:
                plot_machine = PlotMachine(**plot_machine_params)
                result = plot_machine.debug_print()
                print('测试流程中, 请稍等...')
                print(result)
                print('请手动检查打印的命令, 是否与计划中相同, 如果没有问题的话, 就直接点击开始按钮吧!!!')
            except Exception as e:
                print(e)

        if event == 'help_button':
            sg.popup(f"执行流程(经大量测试, 目前最优策略):\n"
                     f"1. 使用SSD作为缓存盘时, 每隔30分钟创建一个任务(使用下一张机械盘), 如果开启了[使用机械盘交替P盘], 则会同时每隔30分钟创建一个使用机械盘作为缓存盘的Plot任务\n"
                     f"2. 以上任务定义为[一波次], 接着, 为了最大化利用CPU(从31%开始仅使用单线程\n"
                     f"   在任务执行到31%时([波次间隔], 一般2-3小时), 同时再开启新一轮Plot任务\n"
                     f"\n"
                     f"举例\n"
                     f"一张1.6T SSD, 2张机械硬盘\n"
                     f"设置[固态最大同时P图数量]为6\n"
                     f"设置[波次间隔]为120, 设置[执行轮次]为20\n"
                     f"执行步骤: \n"
                     f"1. 00:00, 创建2个Plot任务: SSD->机械盘1, 机械盘1->机械盘2\n"
                     f"2. 00:30, 创建2个Plot任务: SSD->机械盘2, 机械盘2->机械盘1  (第1波)\n"
                     f"3. 02:00, 创建1个Plot任务: SSD->机械盘1 \n"
                     f"4. 02:30, 创建1个Plot任务: SSD->机械盘2 (第2波)\n"
                     f"5. 04:00, 创建1个Plot任务: SSD->机械盘1 \n"
                     f"5. 04:30, 创建1个Plot任务: SSD->机械盘2 (第3波)\n"
                     f"以上所有任务, 定义为一轮, 每一轮中同时并发P图8个, 总共执行20轮, 共P图160个, 约16T\n"
                     f"\n"
                     f"举例2(对CPU与内存要求高)\n"
                     f"一张4T SSD,  5张机械盘\n"
                     f"设置[固态最大同时P图数量]为15\n"
                     f"设置[波次间隔]为180, 设置[执行轮次]为20\n"
                     f"执行步骤: \n"
                     f"00:00, 创建2个Plot任务: SSD->机械盘1, 机械盘1->机械盘2\n"
                     f"00:30, 创建2个Plot任务: SSD->机械盘2, 机械盘2->机械盘3\n"
                     f"01:00, 创建2个Plot任务: SSD->机械盘3, 机械盘3->机械盘4\n"
                     f"01:30, 创建2个Plot任务: SSD->机械盘4, 机械盘4->机械盘5\n"
                     f"02:00, 创建2个Plot任务: SSD->机械盘5, 机械盘5->机械盘1 (第1波)\n"
                     f"03:00, 创建1个Plot任务: SSD->机械盘1 \n"
                     f"03:30, 创建1个Plot任务: SSD->机械盘2 \n"
                     f"04:00, 创建1个Plot任务: SSD->机械盘3 \n"
                     f"04:30, 创建1个Plot任务: SSD->机械盘4 \n"
                     f"04:30, 创建1个Plot任务: SSD->机械盘5 (第2波)\n"
                     f"06:00, 创建1个Plot任务: SSD->机械盘1 \n"
                     f"06:30, 创建1个Plot任务: SSD->机械盘2 \n"
                     f"07:00, 创建1个Plot任务: SSD->机械盘3 \n"
                     f"07:30, 创建1个Plot任务: SSD->机械盘4 \n"
                     f"08:00, 创建1个Plot任务: SSD->机械盘5 (第3波)\n"
                     f"以上所有任务, 定义为一轮, 每一轮中同时并发P图20个, 总共执行20轮, 共P图400个, 约40T\n"
                     f"\n"
                     f"参数介绍: \n"
                     f"固态SSD盘\n     - P图使用的主要缓存盘, 目前只支持1个盘\n"
                     f"P图轮次\n     - 官方命令行对应的参数n\n"
                     f"固态最大同时P图数量\n     - 经测试, 1T固态=3, 1.6T=6, 2T=8, 3.2T=12, 3.84T=14, 4T=16"
                     f"任务线程数\n     - 为了最大化CPU, 建议为4, 因为进度31%时(二阶段开始), 便仅使用单线程\n"
                     f"机械盘列表\n     - 使用英文空格隔开\n"
                     f"内存最大使用量\n     - 建议设置为5000以上, 设置大了其实并不会用这么多, 内存也便宜, 内存足够的话建议设置为7000\n"
                     f"P图任务最小间隔\n     - 建议设置30到60\n"
                     f"波次间隔\n     - 建议120-180, 取决于P图一阶段所需要的时间\n"
                     f"是否使用机械盘交替P盘\n     - 每一轮使用机械盘作为缓存盘互相P图, 达到最大化并发P图, 在CPU没有达到100%使用率时, 建议开启这个选项\n"
                     f"farmer公钥\n     - 自己P盘可不填\n"
                     f"矿池公钥\n     - 不加入矿池可不填\n"
                     f"\n"
                     f"可以随意填写参数, 然后点击[测试]按钮, 就会打印出每个P图命令(不会执行)\n"
                     f"这样能清晰得看到自己的任务是怎么执行的",
                     title='帮助', keep_on_top=True)

    window.close()


def main():
    process = Process(target=find_config)
    process.start()
    gui_loop_running()


if __name__ == '__main__':
    freeze_support()
    main()
