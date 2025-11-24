{
  description = "Mul in One unified development shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "aarch64-darwin" "x86_64-darwin" "x86_64-linux" ];

      mkDevShell = system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonEnv = pkgs.python314.withPackages (ps: with ps; [
            pip
            setuptools
            wheel
            pyyaml
            pytest
          ]);
        in
        pkgs.mkShell {
          packages = [
            pythonEnv
            pkgs.uv
            pkgs.git
            pkgs.nodejs_22
            pkgs.nodePackages_latest."@vue/cli"
          ];

          shellHook = ''
            echo "Welcome to the Mul in One dev environment!"
            export PIP_DISABLE_PIP_VERSION_CHECK=1
            export UV_SYSTEM_PYTHON="${pythonEnv}/bin/python3"
            export NPM_CONFIG_PREFIX="$PWD/.npm-global"
            mkdir -p "$NPM_CONFIG_PREFIX"
            export PATH="$NPM_CONFIG_PREFIX/bin:$PATH"
            echo "Python (uv-provided): $(python3 --version)"
            echo "Node: $(node --version)"
            echo "Vue CLI: $(vue --version)"
          '';
        };
    in
    {
      devShells = nixpkgs.lib.genAttrs supportedSystems (system: {
        default = mkDevShell system;
      });
    };
}
