#!/usr/bin/env python3
"""
AFL++ PPO Fuzzing Binary Collector
Automated download and organization of fuzzing benchmark binaries
"""

import os
import sys
import subprocess
import urllib.request
import shutil
from pathlib import Path
from typing import List, Tuple
import json

class BinaryCollector:
    def __init__(self, base_dir: str = "~/fuzz_bins"):
        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.stats = {
            "downloaded": [],
            "failed": [],
            "skipped": []
        }
    
    def log(self, msg: str, level: str = "INFO"):
        prefix = {
            "INFO": "[+]",
            "ERROR": "[!]",
            "SUCCESS": "[✓]",
            "SKIP": "[-]"
        }
        print(f"{prefix.get(level, '[*]')} {msg}")
    
    def download_file(self, url: str, dest: Path, desc: str = "") -> bool:
        """Download file with progress bar"""
        try:
            self.log(f"Downloading: {desc or url}")
            
            def progress_hook(count, block_size, total_size):
                percent = min(int(count * block_size * 100 / total_size), 100)
                bar_len = 40
                filled = int(bar_len * percent / 100)
                bar = '█' * filled + '-' * (bar_len - filled)
                print(f'\r    Progress: |{bar}| {percent}%', end='', flush=True)
            
            urllib.request.urlretrieve(url, dest, progress_hook)
            print()  # New line after progress
            self.stats["downloaded"].append(desc or url)
            return True
        except Exception as e:
            print()
            self.log(f"Failed: {e}", "ERROR")
            self.stats["failed"].append(desc or url)
            return False
    
    def run_command(self, cmd: List[str], cwd: Path = None, desc: str = "") -> bool:
        """Run shell command with error handling"""
        try:
            self.log(f"Running: {desc or ' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=cwd or self.base_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e.stderr}", "ERROR")
            self.stats["failed"].append(desc or ' '.join(cmd))
            return False
    
    def git_clone(self, repo: str, dest: str, branch: str = None, depth: int = 1) -> bool:
        """Clone git repository"""
        dest_path = self.base_dir / dest
        
        if dest_path.exists():
            self.log(f"Already exists: {dest}", "SKIP")
            self.stats["skipped"].append(dest)
            return True
        
        cmd = ["git", "clone", repo, str(dest_path), "--depth", str(depth)]
        if branch:
            cmd.extend(["--branch", branch])
        
        return self.run_command(cmd, desc=f"Cloning {dest}")
    
    def download_lavam(self):
        """Download LAVA-M dataset"""
        self.log("=" * 60)
        self.log("LAVA-M Dataset Collection", "INFO")
        self.log("=" * 60)
        
        lava_dir = self.base_dir / "lava-m"
        lava_dir.mkdir(exist_ok=True)
        
        programs = ["base64", "md5sum", "uniq", "who"]
        base_url = "http://panda.moyix.net/~moyix/lava_corpus/LAVA-M"
        
        for prog in programs:
            filename = f"LAVA-M-{prog}.tar.xz"
            url = f"{base_url}/{filename}"
            dest = lava_dir / filename
            
            if dest.exists():
                self.log(f"Already downloaded: {filename}", "SKIP")
                self.stats["skipped"].append(filename)
                continue
            
            if self.download_file(url, dest, f"LAVA-M {prog}"):
                # Extract
                self.run_command(
                    ["tar", "xf", filename],
                    cwd=lava_dir,
                    desc=f"Extracting {filename}"
                )
        
        # Also try git clone as fallback
        self.git_clone(
            "https://github.com/panda-re/lava.git",
            "lava-m/lava-git",
            depth=1
        )
    
    def download_fuzzbench(self):
        """Download FuzzBench targets"""
        self.log("=" * 60)
        self.log("FuzzBench Targets Collection", "INFO")
        self.log("=" * 60)
        
        self.git_clone(
            "https://github.com/google/fuzzbench.git",
            "fuzzbench",
            depth=1
        )
        
        # List key targets
        targets = [
            "libpng-1.2.56", "libjpeg-turbo-07-2017", "libxml2-v2.9.2",
            "libpcap_fuzz_both", "openssl_x509", "sqlite3_ossfuzz",
            "freetype2-2017", "harfbuzz-1.3.2", "re2-2014-12-09",
            "woff2-2016-05-06"
        ]
        
        self.log(f"Available targets: {', '.join(targets)}")
    
    def download_fuzzer_test_suite(self):
        """Download Google Fuzzer Test Suite"""
        self.log("=" * 60)
        self.log("Google Fuzzer Test Suite Collection", "INFO")
        self.log("=" * 60)
        
        self.git_clone(
            "https://github.com/google/fuzzer-test-suite.git",
            "fuzzer-test-suite",
            depth=1
        )
    
    def download_binutils(self):
        """Download GNU binutils"""
        self.log("=" * 60)
        self.log("GNU Binutils Collection", "INFO")
        self.log("=" * 60)
        
        binutils_dir = self.base_dir / "binutils"
        binutils_dir.mkdir(exist_ok=True)
        
        versions = ["2.26", "2.27", "2.30", "2.35"]
        base_url = "https://ftp.gnu.org/gnu/binutils"
        mirrors = [
            "https://ftp.gnu.org/gnu/binutils",
            "http://mirror.keystealth.org/gnu/binutils",
        ]
        
        for ver in versions:
            filename = f"binutils-{ver}.tar.gz"
            dest = binutils_dir / filename
            
            if dest.exists():
                self.log(f"Already downloaded: {filename}", "SKIP")
                self.stats["skipped"].append(filename)
                continue
            
            # Try mirrors
            success = False
            for mirror in mirrors:
                url = f"{mirror}/{filename}"
                if self.download_file(url, dest, f"binutils {ver}"):
                    success = True
                    break
            
            if not success:
                self.log(f"All mirrors failed for {filename}", "ERROR")
    
    def download_common_targets(self):
        """Download common fuzzing targets"""
        self.log("=" * 60)
        self.log("Common Targets Collection", "INFO")
        self.log("=" * 60)
        
        common_dir = self.base_dir / "common-targets"
        common_dir.mkdir(exist_ok=True)
        
        targets = [
            ("https://download.sourceforge.net/libpng/libpng-1.6.37.tar.gz",
             "libpng-1.6.37.tar.gz", "libpng 1.6.37"),
            
            ("http://www.catb.org/~esr/gif2png/gif2png-2.5.14.tar.gz",
             "gif2png-2.5.14.tar.gz", "gif2png 2.5.14"),
            
            ("https://www.sqlite.org/2023/sqlite-autoconf-3420000.tar.gz",
             "sqlite-autoconf-3420000.tar.gz", "sqlite 3.42.0"),
            
            ("https://www.tcpdump.org/release/tcpdump-4.99.1.tar.gz",
             "tcpdump-4.99.1.tar.gz", "tcpdump 4.99.1"),
            
            ("https://www.tcpdump.org/release/libpcap-1.10.1.tar.gz",
             "libpcap-1.10.1.tar.gz", "libpcap 1.10.1"),
        ]
        
        for url, filename, desc in targets:
            dest = common_dir / filename
            
            if dest.exists():
                self.log(f"Already downloaded: {filename}", "SKIP")
                self.stats["skipped"].append(filename)
                continue
            
            self.download_file(url, dest, desc)
    
    def download_image_parsers(self):
        """Download image format parsers"""
        self.log("=" * 60)
        self.log("Image Parser Collection", "INFO")
        self.log("=" * 60)
        
        image_dir = self.base_dir / "image-parsers"
        image_dir.mkdir(exist_ok=True)
        
        # libjpeg-turbo
        self.git_clone(
            "https://github.com/libjpeg-turbo/libjpeg-turbo.git",
            "image-parsers/libjpeg-turbo",
            branch="2.1.0"
        )
        
        # giflib
        targets = [
            ("https://sourceforge.net/projects/giflib/files/giflib-5.2.1.tar.gz/download",
             "giflib-5.2.1.tar.gz", "giflib 5.2.1"),
        ]
        
        for url, filename, desc in targets:
            dest = image_dir / filename
            if not dest.exists():
                self.download_file(url, dest, desc)
    
    def copy_system_binaries(self):
        """Copy system binaries for quick testing"""
        self.log("=" * 60)
        self.log("System Binaries Collection", "INFO")
        self.log("=" * 60)
        
        system_dir = self.base_dir / "system-bins"
        system_dir.mkdir(exist_ok=True)
        
        binaries = [
            "/usr/bin/file",
            "/usr/bin/readelf",
            "/usr/bin/objdump",
            "/usr/bin/nm",
            "/usr/bin/strings",
            "/usr/bin/size",
            "/usr/bin/sqlite3",
        ]
        
        for bin_path in binaries:
            if not os.path.exists(bin_path):
                self.log(f"Not found: {bin_path}", "SKIP")
                continue
            
            bin_name = os.path.basename(bin_path)
            dest = system_dir / f"{bin_name}-system"
            
            try:
                shutil.copy2(bin_path, dest)
                self.log(f"Copied: {bin_name}", "SUCCESS")
                self.stats["downloaded"].append(bin_name)
            except Exception as e:
                self.log(f"Failed to copy {bin_name}: {e}", "ERROR")
                self.stats["failed"].append(bin_name)
    
    def create_build_scripts(self):
        """Create helper build scripts"""
        self.log("=" * 60)
        self.log("Creating Build Scripts", "INFO")
        self.log("=" * 60)
        
        # AFL++ build wrapper
        build_script = self.base_dir / "build_with_afl.sh"
        build_script.write_text("""#!/bin/bash
# AFL++ Build Wrapper
# Usage: ./build_with_afl.sh <source_dir> <output_name>

if [ $# -lt 2 ]; then
    echo "Usage: $0 <source_dir> <output_name>"
    exit 1
fi

SOURCE_DIR="$1"
OUTPUT_NAME="$2"
BUILD_DIR="$PWD/afl-builds/$OUTPUT_NAME"

export CC="afl-clang-fast"
export CXX="afl-clang-fast++"
export AFL_HARDEN=1

mkdir -p "$BUILD_DIR"
cd "$SOURCE_DIR"

if [ -f "configure" ]; then
    ./configure --prefix="$BUILD_DIR" --disable-shared
    make clean
    make -j$(nproc)
    make install
elif [ -f "CMakeLists.txt" ]; then
    mkdir -p build && cd build
    cmake .. -DCMAKE_INSTALL_PREFIX="$BUILD_DIR"
    make -j$(nproc)
    make install
else
    echo "Unknown build system"
    exit 1
fi

echo "[✓] Built: $OUTPUT_NAME -> $BUILD_DIR"
""")
        build_script.chmod(0o755)
        self.log("Created: build_with_afl.sh", "SUCCESS")
        
        # Quick test script
        test_script = self.base_dir / "quick_test.sh"
        test_script.write_text("""#!/bin/bash
# Quick AFL++ functionality test

echo "[+] Testing AFL++ installation..."

if ! command -v afl-fuzz &> /dev/null; then
    echo "[!] AFL++ not found. Install with: sudo apt install afl++"
    exit 1
fi

echo "[✓] AFL++ found: $(afl-fuzz --version | head -1)"

# Test with system binary
mkdir -p test-in test-out
echo "test" > test-in/seed.txt

echo "[+] Running 10-second test with /usr/bin/file..."
timeout 10 afl-fuzz -i test-in -o test-out -m none -- /usr/bin/file @@ 2>&1 | tail -20

rm -rf test-in test-out

echo "[✓] Test complete!"
""")
        test_script.chmod(0o755)
        self.log("Created: quick_test.sh", "SUCCESS")
    
    def generate_summary(self):
        """Generate collection summary"""
        self.log("=" * 60)
        self.log("Collection Summary", "INFO")
        self.log("=" * 60)
        
        summary = {
            "base_directory": str(self.base_dir),
            "statistics": {
                "downloaded": len(self.stats["downloaded"]),
                "failed": len(self.stats["failed"]),
                "skipped": len(self.stats["skipped"])
            },
            "categories": {
                "LAVA-M": str(self.base_dir / "lava-m"),
                "FuzzBench": str(self.base_dir / "fuzzbench"),
                "Fuzzer Test Suite": str(self.base_dir / "fuzzer-test-suite"),
                "GNU Binutils": str(self.base_dir / "binutils"),
                "Common Targets": str(self.base_dir / "common-targets"),
                "Image Parsers": str(self.base_dir / "image-parsers"),
                "System Binaries": str(self.base_dir / "system-bins")
            },
            "next_steps": [
                f"cd {self.base_dir}",
                "./quick_test.sh  # Test AFL++ installation",
                "cat README.md  # Read full guide",
                "./build_with_afl.sh <source> <name>  # Build targets"
            ]
        }
        
        # Save JSON summary
        summary_file = self.base_dir / "collection_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        self.log(f"Downloaded: {summary['statistics']['downloaded']}", "SUCCESS")
        self.log(f"Failed: {summary['statistics']['failed']}", "ERROR")
        self.log(f"Skipped: {summary['statistics']['skipped']}", "SKIP")
        
        print("\nDirectory Structure:")
        for name, path in summary["categories"].items():
            exists = "✓" if Path(path).exists() else "✗"
            print(f"  {exists} {name}: {path}")
        
        print("\nNext Steps:")
        for step in summary["next_steps"]:
            print(f"  {step}")
        
        print(f"\nFull summary saved to: {summary_file}")
    
    def run_all(self):
        """Run complete collection process"""
        self.log("Starting binary collection for AFL++ PPO experiments...")
        self.log(f"Base directory: {self.base_dir}\n")
        
        try:
            # Download all resources
            self.download_lavam()
            self.download_fuzzbench()
            self.download_fuzzer_test_suite()
            self.download_binutils()
            self.download_common_targets()
            self.download_image_parsers()
            self.copy_system_binaries()
            
            # Create utilities
            self.create_build_scripts()
            
            # Generate summary
            self.generate_summary()
            
            self.log("\n" + "=" * 60, "SUCCESS")
            self.log("Binary collection complete!", "SUCCESS")
            self.log("=" * 60, "SUCCESS")
            
        except KeyboardInterrupt:
            self.log("\nCollection interrupted by user", "ERROR")
            sys.exit(1)
        except Exception as e:
            self.log(f"Unexpected error: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            sys.exit(1)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Collect fuzzing benchmark binaries for AFL++ PPO experiments"
    )
    parser.add_argument(
        "-d", "--dir",
        default="~/fuzz_bins",
        help="Base directory for downloads (default: ~/fuzz_bins)"
    )
    parser.add_argument(
        "--lavam-only",
        action="store_true",
        help="Download only LAVA-M dataset"
    )
    parser.add_argument(
        "--fuzzbench-only",
        action="store_true",
        help="Download only FuzzBench targets"
    )
    parser.add_argument(
        "--binutils-only",
        action="store_true",
        help="Download only GNU binutils"
    )
    
    args = parser.parse_args()
    
    collector = BinaryCollector(args.dir)
    
    if args.lavam_only:
        collector.download_lavam()
    elif args.fuzzbench_only:
        collector.download_fuzzbench()
    elif args.binutils_only:
        collector.download_binutils()
    else:
        collector.run_all()

if __name__ == "__main__":
    main()
