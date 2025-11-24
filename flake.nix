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
          pythonEnv = pkgs.python314;
        in
        pkgs.mkShell {
          packages = [
            pythonEnv
            pkgs.uv
            pkgs.git
            pkgs.nodejs_22
            pkgs.postgresql_16
            pkgs.zsh
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
            export POSTGRES_DATA="$PWD/.postgresql/data"
            mkdir -p "$POSTGRES_DATA"
            echo "PostgreSQL data directory: $POSTGRES_DATA"
            if [ ! -f "$POSTGRES_DATA/PG_VERSION" ]; then
              echo " * Run: initdb -D '$POSTGRES_DATA' --auth=trust"
            else
              echo " * PostgreSQL cluster initialized. Use 'pg_ctl -D $POSTGRES_DATA start'"
            fi

            # Switch to zsh if we are in an interactive shell
            if [[ $- == *i* ]]; then
              exec zsh
            fi
          '';
        };
    in
    {
      devShells = nixpkgs.lib.genAttrs supportedSystems (system: {
        default = mkDevShell system;
      });
    };
}
