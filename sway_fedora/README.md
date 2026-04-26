# Fedora 43 Saway spin initial dot files
Small amount of pre-configurations (bindings, keyboard etc) for fedora sway spin + nwg-shell to have working pc from the start

![screenshot](resources/screenshot.png)

## pre
* fonts: Jetbrains, FontAwesome
* nwg shell (copr tofik/nwg-shell)
* mate-polkit as auth agent

### Shell and fonts
```shell
sudo dnf upgrade -y
sudo dnf install git mate-polkit fontawesome-fonts jetbrains-mono-fonts-all -y

sudo dnf copr enable che/nerd-fonts
sudo dnf install nerd-fonts -y

sudo dnf copr enable tofik/nwg-shell
sudo dnf install nwg-look nwg-displays nwg-shell -y
nwg-shell-installer -a

sudo reboot now
```

### zsh

```
sudo dnf install zsh -y
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

chsh -s $(which zsh)
sudo chsh -s $(which zsh)

dnf config-manager addrepo --from-repofile=https://download.opensuse.org/repositories/shells:zsh-users:zsh-autosuggestions/Fedora_Rawhide/shells:zsh-users:zsh-autosuggestions.repo
dnf install zsh-autosuggestions
```

## Contents
* [foot terminal configs](foot)
* [rofi config](rofi) - I am not using it but some experimental things that was ok to work with
* [sway](sway) - sway keybindings. Main work done here for comfortable navigation
* [waybar](waybar) - Not using. But there is barable waybar configs to start with if I will switch to it
* [xfce4](xfce4) - helper to use foot as default terminal
