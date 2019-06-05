from os import path

from docker.errors import ImageNotFound, BuildError, APIError
from halo import Halo

from . import config
from . import webapi

class CSGOServer:
    def __init__(self, name=None, image=None, ip=None, token=None, config=None,
                 cfgdir=None, docker_client=None):

        self.name = name
        self.image = image
        self.ip = ip
        self.token = token
        self.config = config
        self.cfgdir = cfgdir
        self.docker_client = docker_client

        self.cs_cfg = self.config['cs']
        self.docker_cfg = self.config['docker']

        self.env = {
            'TICKRATE': self.cs_cfg['tickrate'],
            'GSLT': self.token,
            'MAP': self.cs_cfg['map'],
            'MAXPLAYERS': self.cs_cfg['maxplayers'],
            'MAPGROUP': self.cs_cfg['mapgroup'],
            'GAMEMODE': self.cs_cfg['gamemode'],
            'GAMETYPE': self.cs_cfg['gametype'],
            'HOSTNAME': self.name,
            'RCONPW': self.cs_cfg['rcon_pw'],
            'IP': self.ip
        }

        self.vols = {
            self.docker_cfg['demo_vol']: {
                'bind': self.docker_cfg['demo_path'],
                'mode': 'rw'
            }
        }

    def start(self):
        try:
            self.docker_client.containers.get(self.name).start()
        except:
            self.run()

    def run(self):
        try:
            self.docker_client.images.get(self.image)
        except ImageNotFound:
            with Halo(text=f'Image {self.image} not found, building...',
                      spinner='arc') as spin:
                try:
                    self._build_image()
                except BuildError as e:
                    spin.fail(text=f'Image {self.image} build failed!')
                    print(e)
                else:
                    spin.succeed(text=f'Image {self.image} built!')

        c = self.docker_client.containers.run(image=self.image,
                                              name=self.name,
                                              environment=self.env,
                                              volumes=self.vols,
                                              network_mode='host',
                                              privileged=True,
                                              detach=True
                                             )
        self.container_id = c.id
        return c

    def stop(self):
        return self.docker_client.containers.stop(self.name)

    def status(self):
        try:
            return self.docker_client.containers.get(self.name).status
        except:
            return 'notfound'

    def destroy(self, force=False):
        return self.docker_client.containers.get(self.name).remove(v=False,
                                                                   force=force)

    def _build_image(self):
        df = path.abspath(self.docker_cfg['dockerfile'])
        df_path = path.dirname(df)
        args = {'cfgdir': self.cfgdir}

        self.docker_client.images.build(path=df_path, dockerfile=df,
                                        tag=self.image, quiet=False)
