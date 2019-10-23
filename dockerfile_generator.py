"""WOS Docker-Image Generator
Ein Generator Modul um Orginal Dockerfiles in ein eigenes Docker-Image zusammenzubauen
        Es kann ein Config File fuer andere Befehle (Betribsystem abhaengig) hinterlegt werden
        Die Methode writeConfig schreibt ein Config Beispiel File"""

from subprocess import call, check_output
from os.path import isdir, exists, join as pjoin
from os import chdir, getcwd, listdir, environ
from sys import stdin, stdout
from time import sleep
from random import randint
from sys import argv

from configparser import ConfigParser
from tqdm import tqdm
from docker.api.client import APIClient

defaultconf = """
[variable]
dockername=Dockerfile
healthckeck_interval= 300
healthcheck_timeout=3
test_waittime=20
deamon=unix:///var/run/docker.sock
deamon_version=auto
product_tag=latest
old_tag=old
test_tag=temp
latest_tag=latest
fail_tag=fail

[befehle]
git_clean=git pull
git_get=git clone
copy=cp -v
copydir=cp -vr
delete=rm -f
deldir=rm -rf
dockertag=docker tag
dockerpush=docker push
dockerrmi=docker rmi
wget=wget
unzip=unzip
pip_privet_search=pip3 search -i

[betriebsystem]
# Es koenen bis zu 9 Zusatzbefehle eingetragen werden
alpine_1=apk -U update
alpine_2=apk -U upgrade
centos_1=yum -y clean all
centos_2=yum -y update
centos_3=yum -y clean all
debian_1=apt-get -y update
debian_2=apt-get -y upgrade
debian_3=apt-get -y dist-upgrade
debian_4=apt-get -y autoremove
debian_5=apt-get -y clean
ubuntu_1=apt-get -y update
ubuntu_2=apt-get -y upgrade
ubuntu_3=apt-get -y dist-upgrade
ubuntu_4=apt-get -y autoremove
ubuntu_5=apt-get -y clean

[healthttp]
alpine=wget --spider -T 5
centos=curl -f
debian=wget --spider -t 1
ubuntu=wget --spider -t 1
"""
config = ConfigParser()
config.read_string(defaultconf)
if exists("/etc/dockerfile_generator.cfg"):
    config.read("/etc/dockerfile_generator.cfg")
elif exists("/usr/local/etc/dockerfile_generator.cfg"):
    config.read("/usr/local/etc/dockerfile_generator.cfg")
elif exists("dockerfile_generator.cfg"):
    config.read("dockerfile_generator.cfg")
else:
    print("!! Config not found !!")
    exit(1)


class dockerfile_creater():
    def __init__(self, dockerdir=getcwd(), dockername=config.get("variable", "dockername"), registry=config.get("variable", "registry")):
        """Parameter:\n\
            dockerdir: Arbeits Verzeichnis (Default: aktueles Verzeichnis)\n\
            dockername: Filename des generirten Dockerfiles (Default: Dockerfile)\n\
            repository: Docker Repository (Default: dockerregistry:5000)\n\
                Mach der initialisirung kann <Class>.<Variable> manual gesetzt werden:\n\
            .healthttp: Befehl um ein http Test auf diesen Basis-Beriebsystem zu machen"""

        self.git_clean = config.get("befehle", "git_clean").split()
        self.git_get = config.get("befehle", "git_get").split()
        self.copy = config.get("befehle", "copy").split()
        self.copydir = config.get("befehle", "copydir").split()
        self.delete = config.get("befehle", "delete").split()
        self.deldir = config.get("befehle", "deldir").split()
        self.wget = config.get("befehle", "wget").split()
        self.unzip = config.get("befehle", "unzip").split()
        self.pipsearch = config.get("befehle", "pip_privet_search").split()

        self.dockertag = config.get("befehle", "dockertag").split()
        self.dockerpush = config.get("befehle", "dockerpush").split()
        self.dockerrmi = config.get("befehle", "dockerrmi").split()
        environ["DOCKER_HOST"] = config.get("variable", "deamon")
        self.docker_deamon = APIClient(base_url=config.get("variable", "deamon"), version=config.get("variable", "deamon_version"))
        self.pippurl = config.get("variable", "privet_pip")

        self.workdir = getcwd()
        self.dockerfile = []
        self.copyfiles = []
        self.tag = None
        self.gitdir = ""
        self.httpfile = ""

        self.healthhttp = ""

        self.registry = registry
        self.dockerdir = dockerdir
        self.dockername = dockername
        self.ptag = config.get("variable", "product_tag")
        self.otag = config.get("variable", "old_tag")
        self.ttag = config.get("variable", "test_tag")
        self.ltag = config.get("variable", "latest_tag")
        self.ftag = config.get("variable", "fail_tag")
        if len(argv) > 1:
            if argv[1] == "-p":
                self.production = True
        else:
            self.production = False

    # Schreibe Config

    @staticmethod
    def write_config():
        """Schreibt ein Config file Beispiel"""
        with open('dockerfile_generator_example.cfg', 'wb') as configfile:
            config.write(configfile)

    # git Methoden

    def git_clean_m(self, path):
        """Aktualisirt ein Git Verzeichnis\n\
        Parameter: Verzeichnis-Path des Git Repository"""
        chdir(path)
        call(self.git_clean)
        chdir(self.workdir)

    def git_get_m(self, repository):
        """Holt ein git-Repository ins Work Verzeichnis\n\
        Parameter: repository URL von githup. Das root Verzeichnis wird in das Atribut gitdir uebertragen."""
        chdir(self.dockerdir)
        call(self.git_get + [repository])
        self.gitdir = repository.split("/")[-1][:-4]
        self.copyfiles.append(repository.split("/")[-1][:-4])
        chdir(self.workdir)

    # File Methoden in Dockerverzeichnis

    def copy_in(self, pathlist, autoadd=False):
        """Methode um Dateien von Orginal Verzeichnis zum Arbeits Verzeichnis zu kopiren\n\
        Parameter: Liste aus Path Elemeneten zu der zu kopirenden Datei\n\
                   Format: [path, path, ..., kompletter path in gewuenschten git subverzeichnis]\n\
                   autoadd: Programinternen Flack, wird von der add Methode benutzt, nicht manuell benutzen."""
        include_dir = self.path2file(pathlist)
        if autoadd:
            filelist = listdir(include_dir)
            for item in filelist:
                if isdir(pjoin(include_dir, item)):
                    call(self.copydir + [pjoin(include_dir, item), self.dockerdir])
                else:
                    call(self.copy + [pjoin(include_dir, item), self.dockerdir])
            self.copyfiles = self.copyfiles + filelist
        else:
            if isdir(pjoin(include_dir)):
                call(self.copydir + [pjoin(include_dir), self.dockerdir])
            else:
                call(self.copy + [pjoin(include_dir), self.dockerdir])
            self.copyfiles = self.copyfiles + pathlist[-1:]

    def copy_HTTP(self, url):
        """Methode um Dateien von Internet zum Arbeits Verzeichnis zu kopiren\n\
        Parameter: URL zu der zu kopirenden Datei"""
        chdir(self.dockerdir)
        call(self.wget + [url])
        chdir(self.workdir)
        self.httpfile = url.split("/")[-1]
        self.copyfiles.append(url.split("/")[-1])

    def rm_copy_files(self, debug=False):
        """Methode um alle kopirten Orginal Dateien aus den Arbeits Verzeichnis zu loeschen\n\
        Parameter: debug: behalten des generierten Dockerfiles."""
        chdir(self.dockerdir)
        for item in self.copyfiles:
            if isdir(item):
                call(self.deldir + [item])
            else:
                call(self.delete + [item])
        if not debug:
            call(self.delete + [self.dockername])
        chdir(self.workdir)

    # Bearbeite Dockerfile Methoden

    def line_add(self, insert, file=False, nocash=False):
        """Fuegt eine Zeile oder eine Datei in Dockerfile ein\n\
        Parameter: Text der Zeile oder Datei-Pfat"""
        if nocash:
            self.dockerfile.append("RUN echo %i\n" % (randint(1, 100000)))
        if file:
            fh = open(insert, "r")
            for line in fh:
                self.dockerfile.append("%s\n" % line)
            fh.close()
        else:
            self.dockerfile.append("%s\n" % insert)

    def line_del(self, text):
        """Loescht alle Zeilen aus den Dockerfile die einen Suchbegrif enthalten\n\
        Parameter: Suchbegrif"""
        templist = self.dockerfile
        self.dockerfile = []
        for line in templist:
            if line.find(text) > -1:
                continue
            self.dockerfile.append(line)

    def line_rewrite(self, search, text, nocash=False):
        """Ersetzt alle Zeilen aus den Dockerfile die einen Suchbegrif enthalten\n\
        Parameter: search = Suchbegrif\n\
                   text   = Text der zu ersetzenden Zeile"""
        if nocash:
            self.dockerfile.append("RUN echo %i\n" % (randint(1, 100000)))
        templist = self.dockerfile
        self.dockerfile = []
        for line in templist:
            if line.find(search) > -1:
                self.dockerfile.append("%s\n" % text)
            else:
                self.dockerfile.append(line)

    def add_dockerverzeichnis(self, pathlist=None, dirflack=True, delexpose=True, start=False):
        """Fuegt ein Docker Produkt ein\n\
        Parameter:\n\
            pathlist: Liste aus Path Elementen die zum Verzeichnis der importirten Dockerfiles fuehren\n\
                      Das Format der Liste ist [git-Verzeichnis, Subverzeichnis, Subverzeichnis, ...]\n\
                      Ist das Verzeichnis nicht in github mus githup auf False gesetzt werden\n\
                      In Verzeichnis wird eine Datei Names 'Dockerfile' erwartet\n\
            dirflack: Flack ob die Orginaldateien kopiert werden sollen oder nicht (Default: True)\n\
                 ACHTUNG: enthaelt das Verzeichnis eine .dockerignore dann ist ein automatisches kopiren ueber\n\
                          dieses Flack nicht moeglich. Die Dateien muessen manuell mit copy_in-Methode kopiert werden\n\
            delexpose: Flack um EXPOSE angaben zu loeschen (Default: True)\n\
            start: Flack ob das hinzugefuegte Docker Produckt das Start-Base Docker Produkt ist (Default: False)"""
        pathlist = pathlist or []
        if not pathlist:
            stdout.write("\n")
            stdout.write("\nSubverzeichnis zum Dockerfile: \n\n")
            file = stdin.readline()[:-1]
            stdout.write("\n")
        else:
            # gitdir = pathlist[0]
            file = self.path2file(pathlist + ["Dockerfile"])
        fh = open(file, "r")
        for line in fh:
            if line.strip().startswith("FROM") and not start:
                continue
            if line.strip().startswith("EXPOSE") and delexpose:
                continue
            self.dockerfile.append(line)
        fh.close()
        if dirflack:
            self.copy_in(pathlist, autoadd=True)

    def add_uwsgi_product(self, conf_dir, initfile="production.ini", cmd="pserve /production.ini", nocash=True, version=True):
        self.copy_in(conf_dir + [initfile])
        modul_list = []
        iniconf = ConfigParser()
        iniconf.read(initfile)
        modul_list.append(self.rawmodul_to_modul(iniconf['app:main']['use']))
        main_modul = self.rawmodul_to_modul(iniconf['app:main']['use'])
        modul_list.append(main_modul)
        try:
            modul_includes = iniconf['app:main']['pyramid.includes']
            modul_includes = modul_includes.split("\n")
            for modul in modul_includes:
                modul_list.append(self.rawmodul_to_modul(modul))
        except:
            pass

        modul_list = sorted(set(modul_list), key=modul_list.index)
        try:
            modul_list.remove("")
        except:
            pass

        self.dockerfile.append("ADD %s /\n" % initfile)
        self.dockerfile.append("RUN python -VV; pip -V; uname -a\n")
        if nocash:
            self.dockerfile.append("RUN echo %i\n" % (randint(1, 100000)))
        self.dockerfile.append("RUN pip --disable-pip-version-check --no-cache-dir --no-color install %s\n" % (" ".join(modul_list)))
        self.dockerfile.append("CMD %s\n" % cmd)

        if version:
            self.tag = "%s:%s" % (main_modul, self.get_modul_version(main_modul))

    def add_betriebsystem_clean(self, base):
        text = "RUN"
        for i in range(1, 10):
            if config.has_option("betriebsystem", "%s_%i" % (base, i)):
                text = "%s %s \ \n &&" % (text, config.get("betriebsystem", "%s_%i" % (base, i)))
        self.line_add(text[:-7])

    def add_healthcheck(self, command, interval=config.getint("variable", "healthckeck_interval"),
                        timeout=config.getint("variable", "healthcheck_timeout"), httpbase="NONE"):
        """Fuegt eine HEALTHCHECK Zeile in das Dockerfile ein.\n\
            Parameter:\n\
                command: Testbefehl oder URL der Testseite\n\
                interval: in Sekunden\n\
                timeout: in Sekunden\n\
                http: Flack ob das das comando ein Befehl ist oder eine URL"""
        command = self.http_command(httpbase, command)
        self.line_add("HEALTHCHECK --interval=%is --timeout=%is CMD %s || exit 1" % (interval, timeout, command))

    # Dockerfile abarbeiten Methoden

    def start_dockerfile(self, image="scratch", fromreg=True):
        """generiere Dockerfile Header\n\
            image: Tag von Docker - Images das in FROM stehen soll oder welches Base Betribsystem eingebaut werden soll\n\
            base: Betriebsystem auf den das Image basiert"""

        image_list = image.split(":")
        if fromreg and not image == "scratch":
            image = "%s/%s" % (self.registry, image)
            image_list[0] = "%s/%s" % (self.registry, image_list[0])
        if not image == "scratch":
            self.docker_deamon.pull(image_list[0], tag=image_list[1])
        self.dockerfile.append("FROM %s\n" % image)
        chdir(self.workdir)

    def write_dockerfile(self, nogpg=False):
        """Schreibt das generirte Dockerfile ins Arbeitsverzeichnis\n\
        Parameter: Flack um gpg abfragen in Orginal Dockerfile nicht zu uebernemen"""
        fh = open(pjoin(self.dockerdir, self.dockername), "w")
        for line in self.dockerfile:
            if not nogpg:
                fh.writelines(line)
            else:
                if line.find(".asc") > -1 or line.find(" gpg ") > -1:
                    pass
                else:
                    fh.writelines(line)

    def build_image(self, tag=None, nocache=False):
        """Generirt das Docker Images (Tagt die alte Version auf old um)\n\
        Parameter: \n\
            Tag: Tag von Image\n\
            buildoption: Zusatz Optionen zum Build\n\
            errordirclean: Flack ob nach einen fehlgeschlagenen Build das Arbeitsverzeichnis gesaubert werden soll oder nicht"""
        self.tag = tag or self.tag
        if self.tag is None:
            stdout.write("\n")
            stdout.write("Docker-Image Bezeichnung: \n\n")
            self.tag = stdin.readline()[:-1]
            stdout.write("\n")
        if self.existst_tag(self.tag):
            self.retag_and_push(self.tag, "%s:%s" % (self.tag_to_rep(), self.ttag), False)

        output = [line for line in self.docker_deamon.build(self.dockerdir, self.tag, dockerfile=self.dockername, rm=True, nocache=nocache)]
        for line in output:
            line = eval(line)
            if "stream" in line.keys():
                print(line["stream"][:-1])
            if "error" in line.keys():
                print(line["error"])
                exit(1)
        if not self.existst_tag("%s:%s" % (self.tag_to_rep(), self.ttag), self.tag, True):
            self.retag_and_push("%s:%s" % (self.tag_to_rep(), self.ttag), "%s:%s" % (self.tag_to_rep(), self.otag), False)
        if self.existst_tag("%s:%s" % (self.tag_to_rep(), self.ttag)):
            call(self.dockerrmi + ["%s:%s" % (self.tag_to_rep(), self.ttag)])

    def test_image(self, cmd, waittime=config.getint("variable", "test_waittime"), noservice=False, toreg=True, httpbase=None):
        """Testet das generierte Image\n\
        Parameter:\n\
            waittime: Wartezeit bis der Test ausgefuert werden soll in Sekunden um denn Dienst Zeit zu geben zu starten (Default: 20s)\n\
            cmd: Test Befehl\n\
            toreg: Flack um zu bestimmen das das getestete Image in die Registry gepusht wird oder nicht (Default: True)\n\
            noservice: Image ist kein Service-Image\n\
            http: Flack ob das das comando ein Befehl ist oder eine URL"""
        httpbase = httpbase or "NONE"
        cmd = self.http_command(httpbase, cmd)
        if noservice:
            container = self.docker_deamon.create_container(image=self.tag, name="autotest_%s" % (self.tag.split(":")[0]), command="/bin/sh", tty=True)
        else:
            container = self.docker_deamon.create_container(image=self.tag, name="autotest_%s" % (self.tag.split(":")[0]), detach=True)
        self.docker_deamon.start(container["Id"])
        for i in tqdm(range(waittime), ascii=True, desc="Image Test in"):
            sleep(1)
        try:
            execInstantz = self.docker_deamon.exec_create(container["Id"], cmd, tty=True)
        except:
            stdout.write("ERROR:\nImage ist abgestuerzt\n")
            self.image_fail()
            return False
        out_text = self.docker_deamon.exec_start(execInstantz["Id"])
        if self.docker_deamon.exec_inspect(execInstantz["Id"])["ExitCode"] > 0:
            stdout.write("ERROR:\n%s\n" % out_text)
            resolt = False
        else:
            resolt = True
        self.docker_deamon.stop(container["Id"])
        self.docker_deamon.remove_container(container["Id"])
        if resolt:
            self.to_registry(push=toreg)
        else:
            if not resolt:
                self.image_fail()
            exit(1)

    # Registry Methoden

    def to_registry(self, reg=None, push=True):
        """Bennent ein Docker-Image um fuer die Registry (Tagt die alte Version auf old um)\n\
        Parameter: \n\
            reg: Rgistry URL (Default: self.registry)\n\
            push: Flack ob das Docker Image in das Registry gepusht werden soll"""
        reg = reg or self.registry

        if self.existst_tag("%s:%s" % (self.tag_to_rep(), self.otag)):
            self.retag_and_push("%s:%s" % (self.tag_to_rep(), self.otag), "%s/%s:%s" % (reg, self.tag_to_rep(), self.otag), push)

        self.retag_and_push(self.tag, "%s/%s" % (reg, self.tag), push)
        self.retag_and_push(self.tag, "%s/%s:%s" % (reg, self.tag_to_rep(), self.ltag), push)
        if self.production:
            self.retag_and_push(self.tag, "%s/%s:%s" % (reg, self.tag_to_rep(), self.ptag), push)

    def retag_and_push(self, oldtag, newtag, push=True):
        """Aendert ein Tag und Pusht das in die Registry\n\
            Parameter: \n\
                oldtag: existirendes Tag\n\
                newtag: gewuenschtes Tag\n\
                push: Flack ob das neu getackte Image ins Registry gepusht werden soll"""
        call(self.dockertag + [oldtag, newtag])
        if push:
            call(self.dockerpush + [newtag])

    # Docker Image sub Methoden

    def existst_tag(self, tag, stag=None, test_id=False):
        """Sucht ob ein Tag existirt\n\
            Parameter:\n\
                tag: Tag der gesucht wird\n\
                stag: Tag der mit tag verglichen wird wenn testID gesetzt ist\n\
                test_id: Einzeltag suche (False) oder TagID vergleich von tag und stag (True)"""
        stag = stag or ""
        tag_id = "0"
        sorce_id = "1"
        image_list = self.docker_deamon.images(name="%s" % (self.tag_to_rep(tag)))
        for image in image_list:
            if image["RepoTags"] is None:
                continue
            imagetags = image["RepoTags"]
            for imagetag in imagetags:
                if imagetag == tag:
                    if not test_id:
                        return True
                    tag_id = image["Id"]
                if imagetag == stag:
                    sorce_id = image["Id"]
                if tag_id == sorce_id:
                    return True
        return False

    def image_fail(self):
        call(self.dockertag + [self.tag, "%s:%s" % (self.tag_to_rep(), self.ftag)])
        if self.existst_tag("%s:%s" % (self.tag_to_rep(), self.otag)):
            self.retag_and_push("%s:%s" % (self.tag_to_rep(), self.otag), self.tag, False)
            call(self.dockerrmi + ["%s:%s" % (self.tag_to_rep(), self.otag)])

    # String umforatirung Methoden

    @staticmethod
    def http_command(httpbase, cmd):
        if config.has_option("healthttp", httpbase):
            return "%s %s" % (config.get("healthttp", httpbase), cmd)
        else:
            return cmd

    @staticmethod
    def path2file(pathlist):
        """Methode um aus einer Liste von Path Elementen ein Path-string zu erstellen\n\
        Parameter: Liste aus Path Elementen"""
        file = ""
        for item in pathlist:
            file = pjoin(file, item)
        return file

    def tag_to_rep(self, tag=None):
        """Gibt das Repository von einen Tag zurueck\n\
         Parameter: ein Tag (Default: self.tag)"""
        tag = tag or self.tag
        split_tag = tag.split(":")
        return ":".join(split_tag[:-1])

    @staticmethod
    def rawmodul_to_modul(rawmodul):
        rawmodul = rawmodul.split(":", 1)
        if len(rawmodul) > 1:
            rawmodul = rawmodul[1]
        else:
            rawmodul = rawmodul[0]
        rawmodul = rawmodul.split("#", 1)[0]
        rawmodul = rawmodul.split(".", 1)[0]
        return rawmodul

    def get_modul_version(self, modul):
        out = check_output(self.pipsearch + [self.pippurl] + [modul]).decode('utf-8')
        out = out.split("(", 1)[1]
        out = out.split(")", 1)[0]
        return out
