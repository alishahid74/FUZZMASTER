#!/usr/bin/env python3
"""
Automatic AFL++ Fuzzing Framework
Runs multiple benchmarks, monitors progress, finds crashes, generates reports
"""

import os
import sys
import time
import json
import subprocess
import signal
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutomaticFuzzingFramework:
    def __init__(self, project_root, duration_hours=1.0):
        self.project_root = Path(project_root)
        self.duration = duration_hours
        self.results_dir = self.project_root / "results" / "auto-fuzzing"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.fuzzer_processes = []
        self.benchmarks = []
        self.start_time = None
        self.end_time = None
        
    def setup_benchmarks(self):
        """Setup all available benchmarks"""
        logger.info("Setting up benchmarks...")
        
        # Benchmark 1: OpenSSL (if available)
        openssl_bin = self.project_root / "binaries/openssl-1.1.1f/apps/openssl"
        if openssl_bin.exists():
            self.benchmarks.append({
                'name': 'openssl',
                'binary': str(openssl_bin),
                'input_dir': self._create_input_dir('openssl', [
                    ("http.txt", "GET / HTTP/1.0\r\n\r\n"),
                    ("ssl.bin", b"\x16\x03\x01\x00\x05"),
                    ("post.txt", "POST / HTTP/1.1\r\nHost: test\r\n\r\n")
                ]),
                'args': '',
                'parallel': 3  # Run 3 instances for better coverage
            })
            logger.info("✓ OpenSSL benchmark configured")
        
        # Benchmark 2: System binaries (multiple)
        system_benchmarks = [
            {
                'name': 'base64',
                'binary': '/usr/bin/base64',
                'input': [("test.txt", "SGVsbG8gV29ybGQ="), ("test2.txt", "QUFBQQ==")],
                'args': '-d',
                'parallel': 1
            },
            {
                'name': 'xxd',
                'binary': '/usr/bin/xxd',
                'input': [("test.txt", "test data"), ("hex.txt", "48656c6c6f")],
                'args': '@@',
                'parallel': 1
            },
            {
                'name': 'grep',
                'binary': '/usr/bin/grep',
                'input': [("text.txt", "Hello World\nTest\nData"), ("pattern.txt", "search\npattern")],
                'args': '-E "test" @@',
                'parallel': 1
            }
        ]
        
        for bench in system_benchmarks:
            if Path(bench['binary']).exists():
                self.benchmarks.append({
                    'name': bench['name'],
                    'binary': bench['binary'],
                    'input_dir': self._create_input_dir(bench['name'], bench['input']),
                    'args': bench['args'],
                    'parallel': bench.get('parallel', 1)
                })
                logger.info(f"✓ {bench['name']} benchmark configured")
        
        logger.info(f"Total benchmarks configured: {len(self.benchmarks)}")
        return len(self.benchmarks) > 0
    
    def _create_input_dir(self, name, files):
        """Create input directory with seed files"""
        input_dir = self.project_root / "afl-workdir" / f"input-{name}"
        input_dir.mkdir(parents=True, exist_ok=True)
        
        for filename, content in files:
            filepath = input_dir / filename
            if isinstance(content, bytes):
                filepath.write_bytes(content)
            else:
                filepath.write_text(content)
        
        return str(input_dir)
    
    def start_fuzzing(self):
        """Start all fuzzing campaigns"""
        logger.info("="*60)
        logger.info("STARTING AUTOMATIC FUZZING FRAMEWORK")
        logger.info("="*60)
        logger.info(f"Duration: {self.duration} hours")
        logger.info(f"Benchmarks: {len(self.benchmarks)}")
        logger.info("")
        
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=self.duration)
        
        for benchmark in self.benchmarks:
            self._start_benchmark(benchmark)
        
        logger.info("")
        logger.info(f"✓ All fuzzers started! Total: {len(self.fuzzer_processes)}")
        logger.info(f"Will run until: {self.end_time.strftime('%H:%M:%S')}")
        logger.info("")
        
    def _start_benchmark(self, benchmark):
        """Start fuzzing for a single benchmark"""
        name = benchmark['name']
        output_dir = self.results_dir / name
        
        if benchmark.get('parallel', 1) > 1:
            # Start master + slaves for parallel fuzzing
            roles = ['master'] + [f'slave{i}' for i in range(1, benchmark['parallel'])]
            
            for role in roles:
                cmd = self._build_afl_command(
                    benchmark['binary'],
                    benchmark['input_dir'],
                    str(output_dir),
                    benchmark['args'],
                    role if role == 'master' else None,
                    role if role.startswith('slave') else None
                )
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                self.fuzzer_processes.append({
                    'process': process,
                    'benchmark': name,
                    'role': role,
                    'pid': process.pid
                })
                
                logger.info(f"  Started {name} ({role}) - PID: {process.pid}")
                time.sleep(2)  # Stagger starts
        else:
            # Single instance
            cmd = self._build_afl_command(
                benchmark['binary'],
                benchmark['input_dir'],
                str(output_dir),
                benchmark['args']
            )
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.fuzzer_processes.append({
                'process': process,
                'benchmark': name,
                'role': 'default',
                'pid': process.pid
            })
            
            logger.info(f"  Started {name} - PID: {process.pid}")
    
    def _build_afl_command(self, binary, input_dir, output_dir, args, master=None, slave=None):
        """Build AFL++ command"""
        cmd = ['afl-fuzz', '-i', input_dir, '-o', output_dir]
        
        if master:
            cmd.extend(['-M', master])
        elif slave:
            cmd.extend(['-S', slave])
        
        cmd.extend(['-m', 'none', '--'])
        cmd.append(binary)
        
        if args:
            cmd.extend(args.split())
        
        return cmd
    
    def monitor_progress(self):
        """Monitor fuzzing progress and display status"""
        logger.info("Monitoring fuzzing progress...")
        logger.info("Press Ctrl+C to stop early")
        logger.info("")
        
        try:
            while datetime.now() < self.end_time:
                time.sleep(30)  # Check every 30 seconds
                self._display_status()
                
        except KeyboardInterrupt:
            logger.info("\n\nUser interrupted - stopping fuzzers...")
        
        self._display_status(final=True)
    
    def _display_status(self, final=False):
        """Display current fuzzing status"""
        status_lines = []
        status_lines.append("\n" + "="*60)
        
        if final:
            status_lines.append("FINAL FUZZING RESULTS")
        else:
            runtime = datetime.now() - self.start_time
            remaining = self.end_time - datetime.now()
            status_lines.append(f"FUZZING STATUS (Runtime: {runtime}, Remaining: {remaining})")
        
        status_lines.append("="*60)
        
        total_crashes = 0
        total_paths = 0
        
        for benchmark in self.benchmarks:
            name = benchmark['name']
            output_dir = self.results_dir / name
            
            if not output_dir.exists():
                continue
            
            # Count crashes and paths across all instances
            crashes = len(list(output_dir.rglob("crashes/id:*")))
            
            # Get stats from master or default
            stats_files = list(output_dir.rglob("fuzzer_stats"))
            paths = 0
            coverage = 0
            execs = 0
            
            if stats_files:
                stats = self._parse_stats(stats_files[0])
                paths = stats.get('corpus_count', 0)
                coverage = stats.get('bitmap_cvg', 0)
                execs = stats.get('execs_done', 0)
            
            status_lines.append(f"\n{name}:")
            status_lines.append(f"  Crashes: {crashes}")
            status_lines.append(f"  Paths: {paths}")
            status_lines.append(f"  Coverage: {coverage}%")
            status_lines.append(f"  Execs: {execs:,}")
            
            total_crashes += crashes
            total_paths += paths
        
        status_lines.append(f"\n{'='*60}")
        status_lines.append(f"TOTALS: {total_crashes} crashes, {total_paths} paths")
        status_lines.append("="*60)
        
        logger.info("\n".join(status_lines))
    
    def _parse_stats(self, stats_file):
        """Parse AFL++ fuzzer_stats file"""
        stats = {}
        try:
            with open(stats_file) as f:
                for line in f:
                    if ':' in line:
                        key, val = line.strip().split(':', 1)
                        key = key.strip()
                        val = val.strip().rstrip('%')
                        try:
                            stats[key] = int(val)
                        except:
                            try:
                                stats[key] = float(val)
                            except:
                                stats[key] = val
        except:
            pass
        return stats
    
    def stop_fuzzing(self):
        """Stop all fuzzing processes"""
        logger.info("\nStopping all fuzzers...")
        
        for fuzzer in self.fuzzer_processes:
            try:
                fuzzer['process'].terminate()
                fuzzer['process'].wait(timeout=5)
                logger.info(f"  Stopped {fuzzer['benchmark']} ({fuzzer['role']})")
            except:
                try:
                    fuzzer['process'].kill()
                except:
                    pass
        
        logger.info("✓ All fuzzers stopped")
    
    def generate_reports(self):
        """Generate analysis reports"""
        logger.info("\nGenerating reports...")
        
        # Collect all results
        summary = {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration_hours': self.duration,
            'benchmarks': []
        }
        
        for benchmark in self.benchmarks:
            name = benchmark['name']
            output_dir = self.results_dir / name
            
            if not output_dir.exists():
                continue
            
            crashes = list(output_dir.rglob("crashes/id:*"))
            stats_files = list(output_dir.rglob("fuzzer_stats"))
            
            bench_data = {
                'name': name,
                'crashes': len(crashes),
                'crash_files': [str(c) for c in crashes[:10]]  # First 10
            }
            
            if stats_files:
                stats = self._parse_stats(stats_files[0])
                bench_data.update({
                    'paths': stats.get('corpus_count', 0),
                    'coverage': stats.get('bitmap_cvg', 0),
                    'execs': stats.get('execs_done', 0),
                    'stability': stats.get('stability', 0)
                })
            
            summary['benchmarks'].append(bench_data)
        
        # Save summary
        summary_file = self.results_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"✓ Summary saved: {summary_file}")
        
        # Generate markdown report
        report = self._generate_markdown_report(summary)
        report_file = self.results_dir / "FUZZING_REPORT.md"
        report_file.write_text(report)
        
        logger.info(f"✓ Report saved: {report_file}")
        
        return summary
    
    def _generate_markdown_report(self, summary):
        """Generate markdown report"""
        lines = []
        lines.append("# Automatic Fuzzing Framework Results\n")
        lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**Duration**: {summary['duration_hours']} hours\n")
        lines.append(f"**Start Time**: {summary['start_time']}\n")
        lines.append(f"**End Time**: {summary['end_time']}\n\n")
        
        lines.append("## Summary\n")
        total_crashes = sum(b['crashes'] for b in summary['benchmarks'])
        total_paths = sum(b.get('paths', 0) for b in summary['benchmarks'])
        lines.append(f"- **Total Benchmarks**: {len(summary['benchmarks'])}\n")
        lines.append(f"- **Total Crashes Found**: {total_crashes}\n")
        lines.append(f"- **Total Unique Paths**: {total_paths}\n\n")
        
        lines.append("## Benchmark Results\n\n")
        
        for bench in summary['benchmarks']:
            lines.append(f"### {bench['name'].upper()}\n\n")
            lines.append(f"- **Crashes**: {bench['crashes']}\n")
            lines.append(f"- **Unique Paths**: {bench.get('paths', 'N/A')}\n")
            lines.append(f"- **Coverage**: {bench.get('coverage', 'N/A')}%\n")
            lines.append(f"- **Total Executions**: {bench.get('execs', 'N/A'):,}\n")
            lines.append(f"- **Stability**: {bench.get('stability', 'N/A')}\n\n")
            
            if bench['crash_files']:
                lines.append("**Crash Files**:\n")
                for crash in bench['crash_files']:
                    lines.append(f"- `{crash}`\n")
                lines.append("\n")
        
        return "".join(lines)
    
    def run(self):
        """Main execution flow"""
        try:
            # Setup
            if not self.setup_benchmarks():
                logger.error("No benchmarks available!")
                return 1
            
            # Start fuzzing
            self.start_fuzzing()
            
            # Monitor
            self.monitor_progress()
            
            # Stop
            self.stop_fuzzing()
            
            # Generate reports
            summary = self.generate_reports()
            
            # Final message
            logger.info("\n" + "="*60)
            logger.info("FUZZING COMPLETE!")
            logger.info("="*60)
            logger.info(f"Results directory: {self.results_dir}")
            logger.info(f"Total crashes: {sum(b['crashes'] for b in summary['benchmarks'])}")
            logger.info("="*60)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return 1


def main():
    parser = argparse.ArgumentParser(description="Automatic AFL++ Fuzzing Framework")
    parser.add_argument(
        '--project-root',
        default=os.path.expanduser('~/fuzzing-project'),
        help='Project root directory'
    )
    parser.add_argument(
        '--duration',
        type=float,
        default=1.0,
        help='Fuzzing duration in hours (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    framework = AutomaticFuzzingFramework(args.project_root, args.duration)
    sys.exit(framework.run())


if __name__ == '__main__':
    main()
