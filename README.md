<div id="top"></div>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->




<!-- PROJECT LOGO -->
<br />
  <a href="https://github.com/thilojaeggi/WinGetty">
    <img src="https://raw.githubusercontent.com/thilojaeggi/WinGetty/main/src/wingetty.png" alt="Logo" height="128">
  </a>

<h1>WinGetty</h1>

WinGetty is a self-hosted winget package source. It's portable and can run on Linux, Windows, in Docker, locally and in any cloud.
It is currently in version 1.0.0 and is under active development

## 🚀 Features

- Intuitive and easy to use Webinterface
- Add your own packages for internal or customized software with multiple versions, installers including architectures and scope
- Search, list, show and install software - the core winget features all work
- Support for nested installers and installer switches
- Easy updating of package metadata
- Package download counter
- Support for multiple users and authentication
- Support for multiple roles and permissions
- Runs on Windows, Linux etc. using Docker

## 🚧 Not Yet Working or Complete
- Authentication (it's currently [not supported by winget](https://github.com/microsoft/winget-cli-restsource/issues/100))
- Probably other stuff? It's work-in-progress - please submit an issue and/or PR if you notice anything!

## 🧭 Getting Started

### 🐋 Docker
1. Install Docker on your machine. Refer to the [official Docker documentation](https://docs.docker.com/get-docker/) for instructions specific to your operating system.
2. Download the docker-compose.yml file from the main branch.
3. Open the docker-compose.yml file and modify the configuration values according to your preferences.  
The configurable options are:
* WINGETTY_SQLALCHEMY_DATABASE_URI: This parameter allows you to specify the database URI for storing WinGetty's data. By default, it is set to use SQLite with a file named database.db. You can use any database URI supported by SQLAlchemy, such as MySQL or PostgreSQL.
* WINGETTY_SECRET_KEY: This parameter sets the secret key used for securing WinGetty's sessions and other cryptographic operations. Replace the value with a random string.
* WINGETTY_ENABLE_REGISTRATION: By default, user registration is enabled (1). If you want to disable user registration, set this value to 0 after you have created your first user.
* WINGETTY_REPO_NAME: This parameter specifies the name of your WinGetty repository. You can change it to any desired name.
4. Start the WinGetty application using Docker Compose:
`docker-compose up -d`  
This command launches the WinGetty container in the background.
5. Access the web interface by opening your browser and navigating to http://localhost:8080.  
If you're running WinGetty on a remote server, replace localhost with the appropriate IP address or hostname.
6. Upon accessing the web interface for the first time, you will be prompted to register a user, this user will become the admin user by default.

> ⚠️ **Note**: WinGet requires HTTPS for secure communication and without it WinGet will throw an error. It is recommended to put WinGetty behind a reverse proxy with a client-trusted SSL/TLS certificate.  
By using a reverse proxy with HTTPS, you can ensure secure transmission of data between clients and WinGetty. Popular reverse proxy solutions include NGINX, Apache, and Caddy. Please refer to the documentation of your chosen reverse proxy for detailed instructions on configuring SSL/TLS certificates.

### 🪄 Using WinGetty

You can test the WinGet API by opening `http://localhost:8080/wg/information` in a browser or with `curl` / `Invoke-RestMethod`.

Now you can add it as a package source in winget using the command provided in the 'Setup' tab in the webinterface:

```
winget source add -n WinGetty -t "Microsoft.Rest" -a https://wingetty.dev/wg/
```

and query it:

```
❯ winget search Signal -s WinGetty
Name   ID            Version
----------------------------
Signal Signal.Signal 1.0.0
```
and install packages:
```
❯ winget install Signal.Signal -s WinGetty
Found bottom [Signal.Signal] Version 1.0.0
This application is licensed to you by its owner.
Microsoft is not responsible for, nor does it grant any licenses to, third-party packages.
Downloading  https://wingetty.dev/api/download/Signal.Signal/1.0.0/x64/both
  ██████████████████████████████  112 MB /  112 MB
Successfully verified installer hash
Starting package install...
Successfully installed

~ took 12s
❯
```

<hr>
    <a href="https://github.com/thilojaeggi/WinGetty/issues">Report Issue</a>
    ·
    <a href="https://github.com/thilojaeggi/WinGetty/issues">Request Feature</a>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/thilojaeggi/wingetty.svg?style=flat-square
[contributors-url]: https://github.com/thilojaeggi/WinGetty/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/thilojaeggi/WinGetty.svg?style=flat-square
[forks-url]: https://github.com/thilojaeggi/WinGetty/network/members
[stars-shield]: https://img.shields.io/github/stars/thilojaeggi/WinGetty.svg?style=flat-square
[stars-url]: https://github.com/thilojaeggi/WinGetty/stargazers
[issues-shield]: https://img.shields.io/github/issues/thilojaeggi/WinGetty.svg?style=flat-square
[issues-url]: https://github.com/thilojaeggi/WinGetty/issues
[license-shield]: https://img.shields.io/github/license/thilojaeggi/WinGetty.svg?style=flat-square
[license-url]: https://github.com/thilojaeggi/WinGetty/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=flat-square&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/linkedin_username
[product-screenshot]: images/screenshot.png
[Next.js]: https://img.shields.io/badge/next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white
[Next-url]: https://nextjs.org/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[Vue.js]: https://img.shields.io/badge/Vue.js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D
[Vue-url]: https://vuejs.org/
[Angular.io]: https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white
[Angular-url]: https://angular.io/
[Svelte.dev]: https://img.shields.io/badge/Svelte-4A4A55?style=for-the-badge&logo=svelte&logoColor=FF3E00
[Svelte-url]: https://svelte.dev/
[Laravel.com]: https://img.shields.io/badge/Laravel-FF2D20?style=for-the-badge&logo=laravel&logoColor=white
[Laravel-url]: https://laravel.com
[Bootstrap.com]: https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white
[Bootstrap-url]: https://getbootstrap.com
[JQuery.com]: https://img.shields.io/badge/jQuery-0769AD?style=for-the-badge&logo=jquery&logoColor=white
[JQuery-url]: https://jquery.com
[Flutter]: https://img.shields.io/badge/Flutter-%2302569B.svg?style=for-the-badge&logo=Flutter&logoColor=white
[Flutter-url]: https://flutter.dev
[Dart]: https://img.shields.io/badge/dart-%230175C2.svg?style=for-the-badge&logo=dart&logoColor=white
[Dart-url]: https://dart.dev
[Swift]: https://img.shields.io/badge/swift-F54A2A?style=for-the-badge&logo=swift&logoColor=white
[Swift-url]: https://www.swift.org/
