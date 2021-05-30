from multiprocessing import Pool
from time import sleep
import os


class PlotMachine:

    def __init__(self,
                 plot_k=32,
                 plot_num=20,
                 plot_buffer=7000,
                 plot_threads_num=4,
                 farmer_public_key=None,
                 pool_public_key=None,
                 ssd_dir=(r"G:/",),
                 ssd_plots_count=2,
                 disks=(r"Z:/", r"V:/"),
                 plot_interval=30,
                 one_turn_interval=3.5 * 60,
                 ssd_parrel_num=2,
                 plot_on_spinning_disk=True,
                 debug=True):

        self.plot_k = int(plot_k)
        self.plot_num = int(plot_num)
        self.plot_buffer = int(plot_buffer)
        self.plot_threads_num = int(plot_threads_num)
        self.farmer_public_key = f"-f {farmer_public_key} " if farmer_public_key else ""
        self.pool_public_key = f"-p {pool_public_key} " if pool_public_key else ""

        self.ssds = ssd_dir
        self.ssd_plots_count = ssd_plots_count
        self.disks = disks
        self.disk_plots_count = len(disks)
        self.plot_interval = int(plot_interval)
        self.one_turn_interval = int(one_turn_interval)
        self.ssd_parrel_num = ssd_parrel_num
        self.plot_on_spinning_disk = plot_on_spinning_disk
        self.debug = debug

        # create dir
        self.ssd_dirs = []
        self.final_dirs = []
        self.temp_dirs = []
        for ssd in self.ssds:
            temp_dir = os.path.join(ssd, 't')
            if not os.path.exists(temp_dir):
                os.mkdir(temp_dir)
            self.ssd_dirs.append(temp_dir)
        for disk in self.disks:
            final_dir = os.path.join(disk, 'f')
            temp_dir = os.path.join(disk, 't')
            if not os.path.exists(final_dir):
                os.mkdir(final_dir)
            if not os.path.exists(temp_dir):
                os.mkdir(temp_dir)
            self.final_dirs.append(final_dir)
            self.temp_dirs.append(temp_dir)

        # find chia exe
        self.chia_exe = self._find_exe()
        if not self.chia_exe:
            raise ValueError(r'没有找到chia.exe文件, 请确认安装在了例如: C:\Users\Admin\AppData\Local\chia-blockchain\app-1.1.6\resources\app.asar.unpacked\daemon\chia.exe')

    def _find_exe(self):
        # find cmd
        d = 'C:/'
        d = os.path.join(d, 'Users')
        user_names = []
        for root, dirs, files in os.walk(d, topdown=True):
            for i in dirs:
                user_names.append(i)
            break
        chia_blockchain_dir = None
        for user_name in user_names:
            guess_dir = os.path.join(d, user_name, 'AppData', 'Local', 'chia-blockchain')
            if os.path.exists(guess_dir):
                chia_blockchain_dir = guess_dir
                break
        if not chia_blockchain_dir:
            return
        exe_file = None
        for root, dirs, files in os.walk(chia_blockchain_dir, topdown=True):
            for i in dirs:
                if i.startswith('app-'):
                    exe_file = os.path.join(chia_blockchain_dir, i, 'resources', 'app.asar.unpacked', 'daemon',
                                            'chia.exe')
                    break
            break
        if not exe_file or not os.path.exists(exe_file):
            return

        return exe_file

    def build_cmd_str(self, temp_dir, final_dir):
        cmd_str = f"{self.chia_exe} plots create -k {self.plot_k} -n {self.plot_num} -b {self.plot_buffer} -r {self.plot_threads_num} {self.farmer_public_key}{self.pool_public_key}-t {temp_dir} -d {final_dir}"
        return cmd_str

    def plot(self, temp_dir, final_dir):
        os.system(self.build_cmd_str(temp_dir, final_dir))

    def start_plot(self, pool=None):
        pool = pool or Pool(self.ssd_plots_count + self.disk_plots_count)

        plot_count = 0

        for cur_count in range(9999):
            print(f"cur_count: {cur_count}")

            # use spinning disk
            if self.plot_on_spinning_disk:
                if cur_count < self.disk_plots_count:
                    t = self.temp_dirs[cur_count % self.disk_plots_count]
                    f = self.final_dirs[(cur_count % self.disk_plots_count) - 1]
                    cmd_str = self.build_cmd_str(t, f)
                    print('执行命令: ', cmd_str)
                    plot_count += 1
                    if not self.debug:
                        pool.apply_async(self.plot, args=(t, f))

            # use ssd to plots
            if cur_count < self.ssd_plots_count:
                t = self.ssd_dirs[0]
                f = self.final_dirs[cur_count % self.disk_plots_count]
                cmd_str = self.build_cmd_str(t, f)
                print('执行命令: ', cmd_str)
                plot_count += 1
                if not self.debug:
                    pool.apply_async(self.plot, args=(t, f))

            # all plots done
            max_count = max(self.ssd_plots_count,
                            self.disk_plots_count) if self.plot_on_spinning_disk else self.ssd_plots_count

            if cur_count + 1 >= max_count:
                break

            if cur_count % self.disk_plots_count != self.disk_plots_count - 1:
                print(f"暂停{self.plot_interval}分钟")
                sleep(self.plot_interval * 60) if not self.debug else None
            else:
                paus = self.one_turn_interval - self.disk_plots_count * self.plot_interval
                print(f"一轮完毕 暂停{int(paus)}分钟")
                sleep(paus * 60) if not self.debug else None

        print(f"任务完成, 共Plot {plot_count}个")

        pool.close()
        # pool.join()

    def debug_print(self):

        debug_output = []
        plot_count = 0

        for cur_count in range(9999):

            # use spinning disk
            if self.plot_on_spinning_disk:
                if cur_count < self.disk_plots_count:
                    t = self.temp_dirs[cur_count % self.disk_plots_count]
                    f = self.final_dirs[(cur_count % self.disk_plots_count) - 1]
                    cmd_str = self.build_cmd_str(t, f)
                    debug_output.append(f'模拟执行命令: \n{cmd_str}')
                    plot_count += 1

            # use ssd to plots
            if cur_count < self.ssd_plots_count:
                t = self.ssd_dirs[0]
                f = self.final_dirs[cur_count % self.disk_plots_count]
                cmd_str = self.build_cmd_str(t, f)
                debug_output.append(f'模拟执行命令: \n{cmd_str}')
                plot_count += 1

            # all plots done
            max_count = max(self.ssd_plots_count,
                            self.disk_plots_count) if self.plot_on_spinning_disk else self.ssd_plots_count

            if cur_count + 1 >= max_count:
                break

            if cur_count % self.disk_plots_count != self.disk_plots_count - 1:
                debug_output.append(f"模拟暂停{self.plot_interval}分钟")
                sleep(self.plot_interval * 60) if not self.debug else None
            else:
                paus = self.one_turn_interval - self.disk_plots_count * self.plot_interval
                debug_output.append(f"一波完毕 模拟暂停{int(paus)}分钟")
                sleep(paus * 60) if not self.debug else None

        debug_output.append(f"模拟P图任务完成, 共Plot {plot_count}个")

        return '\n'.join(debug_output)
