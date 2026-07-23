import os
import subprocess
import tempfile
import pathlib
import hashlib
import json
import sys

ROOT = pathlib.Path(__file__).parent.parent

with open(os.path.join(ROOT, "templates", "standalone-tikz.tex"), 'r') as f:
    TEMPLATE = f.read()

def get_file_hash(filepath: str) -> str:
    h = hashlib.sha256()
    h.update(os.path.abspath(filepath).encode('utf-8'))
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def render_tikz(filepath: str, output_dir: str, cache: dict, force: bool = False) -> bool:
    name = pathlib.Path(filepath).stem
    
    # Check cache
    try:
        current_hash = get_file_hash(filepath)
    except Exception as e:
        print(f"Error hashing {filepath}: {e}")
        return False

    svg_file = os.path.join(output_dir, f"{name}.svg")
    target_pdf_file = os.path.join(output_dir, f"{name}.pdf")

    if not force and filepath in cache:
        if cache[filepath] == current_hash and os.path.exists(svg_file) and os.path.exists(target_pdf_file):
            print(f"Skipping {name} (cached)")
            return True

    # Compile the file
    with open(filepath, 'r') as f:
        content = f.read()

    # Determine if it's tikz or tikzcd
    if 'tikzcd' in filepath:
        # Wrap in shorthand or ensure environment is correct
        pass

    # The standalone template's insertion marker changed from "$body$" to the
    # QTikz-style "<>" (see templates/standalone-tikz.tex); support both so a
    # marker mismatch can never again produce blank renders silently.
    if "<>" in TEMPLATE:
        tex_content = TEMPLATE.replace("<>", content)
    elif "$body$" in TEMPLATE:
        tex_content = TEMPLATE.replace("$body$", content)
    else:
        raise RuntimeError("standalone-tikz.tex has no insertion marker (<> or $body$)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = os.path.join(tmpdir, f"{name}.tex")
        with open(tex_file, 'w') as f:
            f.write(tex_content)
        
        # Compile to PDF
        try:
            # Use -interaction=nonstopmode for speed
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", f"-output-directory={tmpdir}", tex_file],
                cwd=tmpdir, check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Error compiling {filepath}:")
            print(e.stdout)
            print(e.stderr)
            return False

        pdf_file = os.path.join(tmpdir, f"{name}.pdf")
        
        # Convert to SVG
        try:
            subprocess.run(["pdf2svg", pdf_file, svg_file], check=True)
            import shutil
            shutil.copy(pdf_file, target_pdf_file)
        except subprocess.CalledProcessError as e:
            print(f"Error converting {pdf_file} to SVG or copying PDF:")
            return False
            
    print(f"Rendered {name}.svg")
    # Update cache
    cache[filepath] = current_hash
    return True

def main():
    output_dir = pathlib.Path("/home/dzack/.pandoc/figures/rendered")
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_file = output_dir / ".cache.json"

    # Command-line argument parsing
    args = sys.argv[1:]
    
    clean_cache = False
    force = False
    
    # Process flags
    if "--clean-cache" in args or "--clear-cache" in args:
        clean_cache = True
        args = [a for a in args if a not in ("--clean-cache", "--clear-cache")]
        
    if "--force" in args or "-f" in args:
        force = True
        args = [a for a in args if a not in ("--force", "-f")]

    if clean_cache:
        if cache_file.exists():
            try:
                cache_file.unlink()
                print("Cache cleared forcefully.")
            except Exception as e:
                print(f"Error clearing cache: {e}")
                sys.exit(1)
        else:
            print("Cache is already empty.")
        if not args:
            sys.exit(0)

    # The pandoc::render-figures recipe invokes this with no arguments; default
    # to rendering everything rather than erroring.
    target = args[0].strip() if args else "--all"

    # Load cache
    cache = {}
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            pass

    # Helper function to save cache
    def save_cache():
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    if target == "--all":
        tikz_dirs = [
            pathlib.Path("/home/dzack/.pandoc/figures/tikz"),
            pathlib.Path("/home/dzack/.pandoc/figures/tikzcd")
        ]

        success = True
        for tikz_dir in tikz_dirs:
            if not tikz_dir.exists():
                print(f"Directory {tikz_dir} does not exist. Skipping.")
                continue
            for tex_file in tikz_dir.glob("*.tex"):
                if not render_tikz(str(tex_file), str(output_dir), cache, force):
                    success = False

        save_cache()
        if not success:
            sys.exit(1)
        sys.exit(0)

    # Single target resolution
    target_path = pathlib.Path(target)
    if not target_path.exists():
        base_dir = pathlib.Path("/home/dzack/.pandoc/figures")
        potential_path = base_dir / target
        if potential_path.exists():
            target_path = potential_path
        else:
            for sub in ["tikz", "tikzcd"]:
                p = base_dir / sub / target
                if p.exists():
                    target_path = p
                    break
                p_tex = base_dir / sub / f"{target}.tex"
                if p_tex.exists():
                    target_path = p_tex
                    break
    
    if not target_path.exists() or not target_path.is_file():
        print(f"Error: File '{target}' not found.")
        sys.exit(1)
    
    print(f"Rendering single file: {target_path}")
    success = render_tikz(str(target_path), str(output_dir), cache, force)
    save_cache()
    
    if not success:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
