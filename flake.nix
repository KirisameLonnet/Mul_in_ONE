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
          pythonEnv = pkgs.python312;
        in
        pkgs.mkShell {
          packages = [
            pythonEnv
            pkgs.uv
            pkgs.git
            pkgs.nodejs_22
            pkgs.postgresql_16
            pkgs.docker
            pkgs.docker-compose
            (if pkgs.stdenv.isDarwin then pkgs.colima else null)
            pkgs.zsh
            pkgs.stdenv.cc.cc.lib
          ];

          shellHook = ''
            echo "Welcome to the Mul in One dev environment!"
            export PIP_DISABLE_PIP_VERSION_CHECK=1
            # Note: UV_SYSTEM_PYTHON not set - let uv manage venv Python version
            export NPM_CONFIG_PREFIX="$PWD/.npm-global"
            mkdir -p "$NPM_CONFIG_PREFIX"
            export PATH="$NPM_CONFIG_PREFIX/bin:$PATH"
            export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:''${LD_LIBRARY_PATH:-}"
            echo "Python (uv-provided): $(python3 --version)"
            echo "Node: $(node --version)"
            export POSTGRES_DATA="$PWD/.postgresql/data"
            export POSTGRES_RUN_DIR="$PWD/.postgresql/run"
            mkdir -p "$POSTGRES_DATA"
            mkdir -p "$POSTGRES_RUN_DIR"
            echo "PostgreSQL data directory: $POSTGRES_DATA"
            echo "PostgreSQL run directory: $POSTGRES_RUN_DIR"
            if [ ! -f "$POSTGRES_DATA/PG_VERSION" ]; then
              echo " * Run: ./scripts/db_control.sh start"
            else
              echo " * PostgreSQL cluster initialized. Use './scripts/db_control.sh start'"
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
