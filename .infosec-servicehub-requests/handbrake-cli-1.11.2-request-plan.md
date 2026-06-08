# InfoSec Request Plan: HandBrakeCLI 1.11.2

- Request date: 2026-06-08
- Minimum target date: 2026-06-11
- Repository: betTube Studio
- Repo path: `/Users/davidmontgomery/bettube-studio`
- Source release: https://github.com/HandBrake/HandBrake/releases/tag/1.11.2
- Release published: 2026-06-07T19:08:25Z
- Authorising manager: Alan Reed (`alanreed`)

## Classification

- Service Hub route: Download File / Software Download Request
- Type of download: Application
- Application file type / package type: Other
- Is this an update to an existing application?: No
- Reason: User corrected the prior update answer as intended for something else. This is a new approval/download request for an external CLI tool needed by the repo.
- Live-form status: all required fields filled; awaiting explicit submit confirmation.

## Plain Business Justification

Need approval to use HandBrakeCLI 1.11.2 for betTube Studio.

betTube Studio renders and manages local MP4 video projects. HandBrakeCLI is needed as a cross-platform command-line video transcode/compression tool for repo workflows where we need consistent MP4 optimisation across Windows, macOS, and Linux.

This is for approved project use only. We will use the upstream GitHub release files and signature files, and will not commit downloaded binaries into the repo.

## Expected Files

Windows CLI:

- `HandBrakeCLI-1.11.2-win-x86_64.zip`
- `HandBrakeCLI-1.11.2-win-x86_64.zip.sig`
- `HandBrakeCLI-1.11.2-win-aarch64.zip`
- `HandBrakeCLI-1.11.2-win-aarch64.zip.sig`

macOS CLI:

- `HandBrakeCLI-1.11.2.dmg`
- `HandBrakeCLI-1.11.2.dmg.sig`

Linux:

- No dedicated Linux HandBrakeCLI binary is listed in the upstream 1.11.2 release assets.
- Approval requested for Linux use from upstream Linux-consumable artefacts/source/packaging where needed:
  - `HandBrake-1.11.2-source.tar.bz2`
  - `HandBrake-1.11.2-source.tar.bz2.sig`
  - `HandBrake-1.11.2-x86_64.flatpak`
  - `HandBrake-1.11.2-x86_64.flatpak.sig`
  - `HandBrake.Plugin.IntelMediaSDK-1.11.2-x86_64.flatpak`
  - `HandBrake.Plugin.IntelMediaSDK-1.11.2-x86_64.flatpak.sig`

## Source URLs

- https://github.com/HandBrake/HandBrake/releases/tag/1.11.2
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrakeCLI-1.11.2-win-x86_64.zip
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrakeCLI-1.11.2-win-x86_64.zip.sig
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrakeCLI-1.11.2-win-aarch64.zip
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrakeCLI-1.11.2-win-aarch64.zip.sig
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrakeCLI-1.11.2.dmg
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrakeCLI-1.11.2.dmg.sig
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrake-1.11.2-source.tar.bz2
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrake-1.11.2-source.tar.bz2.sig
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrake-1.11.2-x86_64.flatpak
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrake-1.11.2-x86_64.flatpak.sig
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrake.Plugin.IntelMediaSDK-1.11.2-x86_64.flatpak
- https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrake.Plugin.IntelMediaSDK-1.11.2-x86_64.flatpak.sig

## Warnings / Pauses

- The Service Hub pre-approved/blacklisted confirmation should only be ticked after the user confirms those lists have been checked.
- Do not submit until the user confirms submission in the browser workflow.
- User confirmed the pre-approved/blacklisted check on 2026-06-08.
- Live form currently has authorising manager `alanreed`, target date `Jun 11, 2026`, login required `No`, and package type `Other`.
