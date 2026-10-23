{ pkgs }: {
  # Python and Node come from .replit modules. Bootstrap uv outside the
  # read-only Nix store so older import environments can still evaluate.
  deps = [];
}
