#!/usr/bin/env python3
import os
import re
import sys
import argparse
import json
from datetime import datetime
from collections import defaultdict

try:
    import scapy.all as scapy
except ImportError:
    print("Error: Scapy is required. Install it using 'pip install scapy'")
    sys.exit(1)

# Define regex patterns for common credentials and sensitive data
PATTERNS = {
    'url': re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!$&\'()*+,;=:@/~]+)*'),
    'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    'username': re.compile(r'(?:username|user|login|email)=([^&\s]+)', re.IGNORECASE),
    'password': re.compile(r'(?:password|pass|pwd)=([^&\s]+)', re.IGNORECASE),
    'auth_basic': re.compile(r'Authorization: Basic (.+)', re.IGNORECASE),
    'auth_bearer': re.compile(r'Authorization: Bearer (.+)', re.IGNORECASE),
    'api_key': re.compile(r'(?:api[-_]?key|access[-_]?token|auth[-_]?token)=([^&\s]+)', re.IGNORECASE),
    'jwt': re.compile(r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'),
    'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    'android_id': re.compile(r'\b[a-f0-9]{16}\b', re.IGNORECASE),  # Android device IDs
    'firebase': re.compile(r'https://[a-z0-9-]+\.firebaseio\.com'),  # Firebase database URLs
}

# HTTP specific patterns
HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE', 'CONNECT']
HTTP_REQUEST_PATTERN = re.compile(r'(' + '|'.join(HTTP_METHODS) + r')\s+([^\s]+)\s+HTTP/[0-9.]+')
HTTP_HOST_PATTERN = re.compile(r'Host:\s+([^\r\n]+)', re.IGNORECASE)
HTTP_CONTENT_TYPE_PATTERN = re.compile(r'Content-Type:\s+([^\r\n]+)', re.IGNORECASE)
HTTP_USER_AGENT_PATTERN = re.compile(r'User-Agent:\s+([^\r\n]+)', re.IGNORECASE)
HTTP_COOKIE_PATTERN = re.compile(r'Cookie:\s+([^\r\n]+)', re.IGNORECASE)

class PcapAnalyzer:
    def __init__(self, pcap_file, output_dir="./forensic_output", verbose=False):
        self.pcap_file = pcap_file
        self.output_dir = output_dir
        self.verbose = verbose
        self.findings = {
            'urls': [],
            'emails': [],
            'credentials': [],
            'auth_tokens': [],
            'api_keys': [],
            'jwts': [],
            'sensitive_numbers': [],
            'http_requests': [],
            'connections': {},
            'dns_queries': [],
            'user_agents': [],
            'cookies': [],
        }
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def log(self, message):
        """Print log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[*] {message}")
    
    def extract_text_from_packet(self, packet):
        """Extract readable text from packet payload"""
        if scapy.Raw in packet:
            try:
                return packet[scapy.Raw].load.decode('utf-8', errors='ignore')
            except:
                return packet[scapy.Raw].load.decode('latin-1', errors='ignore')
        return ""
    
    def scan_for_patterns(self, text, src_ip, dst_ip, timestamp, port=None):
        """Scan packet text for interesting patterns"""
        for pattern_name, pattern in PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                for match in matches:
                    finding = {
                        'value': match,
                        'src_ip': src_ip,
                        'dst_ip': dst_ip,
                        'timestamp': timestamp,
                        'port': port
                    }
                    
                    if pattern_name == 'url':
                        self.findings['urls'].append(finding)
                    elif pattern_name == 'email':
                        self.findings['emails'].append(finding)
                    elif pattern_name in ['username', 'password']:
                        finding['type'] = pattern_name
                        self.findings['credentials'].append(finding)
                    elif pattern_name in ['auth_basic', 'auth_bearer']:
                        finding['type'] = pattern_name
                        self.findings['auth_tokens'].append(finding)
                    elif pattern_name == 'api_key':
                        self.findings['api_keys'].append(finding)
                    elif pattern_name == 'jwt':
                        self.findings['jwts'].append(finding)
                    elif pattern_name == 'credit_card':
                        finding['type'] = pattern_name
                        self.findings['sensitive_numbers'].append(finding)
    
    def extract_http_info(self, text, src_ip, dst_ip, timestamp, port=None):
        """Extract HTTP request information"""
        # Look for HTTP requests
        http_matches = HTTP_REQUEST_PATTERN.search(text)
        if http_matches:
            method = http_matches.group(1)
            path = http_matches.group(2)
            
            # Look for Host header
            host_match = HTTP_HOST_PATTERN.search(text)
            host = host_match.group(1) if host_match else "Unknown"
            
            # Reconstruct full URL
            full_url = f"http://{host}{path}" if not path.startswith('http') else path
            
            # Extract content type
            content_type_match = HTTP_CONTENT_TYPE_PATTERN.search(text)
            content_type = content_type_match.group(1) if content_type_match else "Unknown"
            
            # Extract User-Agent
            user_agent_match = HTTP_USER_AGENT_PATTERN.search(text)
            if user_agent_match:
                user_agent = user_agent_match.group(1)
                self.findings['user_agents'].append({
                    'user_agent': user_agent,
                    'src_ip': src_ip,
                    'timestamp': timestamp
                })
            
            # Extract Cookies
            cookie_match = HTTP_COOKIE_PATTERN.search(text)
            if cookie_match:
                cookies = cookie_match.group(1)
                self.findings['cookies'].append({
                    'cookies': cookies,
                    'host': host,
                    'src_ip': src_ip,
                    'timestamp': timestamp
                })
            
            # Extract form data for POST requests
            form_data = {}
            if method == "POST" and "application/x-www-form-urlencoded" in content_type:
                # Find the form data in the body
                body_parts = text.split('\r\n\r\n')
                if len(body_parts) > 1:
                    body = body_parts[1]
                    for param in body.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            form_data[key] = value
            
            self.findings['http_requests'].append({
                'method': method,
                'url': full_url,
                'host': host,
                'content_type': content_type,
                'form_data': form_data,
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'timestamp': timestamp,
                'port': port
            })
            return True
        return False
    
    def analyze_pcap(self):
        """Main analysis function"""
        
        # Load PCAP file
        try:
            packets = scapy.rdpcap(self.pcap_file)
        except Exception as e:
            print(f"Error reading PCAP file: {e}")
            return
        
        
        # Analyze each packet
        for i, packet in enumerate(packets):
                
            if scapy.IP in packet:
                src_ip = packet[scapy.IP].src
                dst_ip = packet[scapy.IP].dst
                timestamp = datetime.fromtimestamp(float(packet.time)).strftime('%Y-%m-%d %H:%M:%S')
                
                # Identify protocol and ports
                if scapy.TCP in packet:
                    src_port = packet[scapy.TCP].sport
                    dst_port = packet[scapy.TCP].dport
                elif scapy.UDP in packet:
                    src_port = packet[scapy.UDP].sport
                    dst_port = packet[scapy.UDP].dport
                else:
                    src_port = None
                    dst_port = None
                
                # Track connections
                conn_key = f"{src_ip}:{src_port}-{dst_ip}:{dst_port}"
                if conn_key not in self.findings['connections']:
                    self.findings['connections'][conn_key] = {
                        'src_ip': src_ip,
                        'src_port': src_port,
                        'dst_ip': dst_ip,
                        'dst_port': dst_port,
                        'packets': 0,
                        'bytes': 0,
                        'start_time': timestamp,
                        'end_time': timestamp
                    }
                
                self.findings['connections'][conn_key]['packets'] += 1
                self.findings['connections'][conn_key]['bytes'] += len(packet)
                self.findings['connections'][conn_key]['end_time'] = timestamp
                
                # Extract text payload for TCP or UDP
                if (scapy.TCP in packet or scapy.UDP in packet) and scapy.Raw in packet:
                    payload_text = self.extract_text_from_packet(packet)
                    if payload_text:
                        # Scan for patterns
                        self.scan_for_patterns(payload_text, src_ip, dst_ip, timestamp, dst_port)
                        
                        # Extract HTTP info (if present)
                        self.extract_http_info(payload_text, src_ip, dst_ip, timestamp, dst_port)
        
        self.save_results()
        self.print_summary()
    
    def save_results(self):
        """Save results to JSON file"""
        output_file = os.path.join(self.output_dir, f"{os.path.basename(self.pcap_file)}_forensic_results.json")
        with open(output_file, 'w') as f:
            json.dump(self.findings, f, indent=4)
        
        
        # Create individual files for each category
        for category in self.findings:
            if category == 'connections':
                # Connections is a dict, handle differently
                connections_file = os.path.join(self.output_dir, f"{os.path.basename(self.pcap_file)}_connections.txt")
                with open(connections_file, 'w') as f:
                    for conn_key, conn_data in self.findings['connections'].items():
                        f.write(f"{conn_key}:\n")
                        for k, v in conn_data.items():
                            f.write(f"  {k}: {v}\n")
                        f.write("\n")
            elif isinstance(self.findings[category], list) and self.findings[category]:
                category_file = os.path.join(self.output_dir, f"{os.path.basename(self.pcap_file)}_{category}.txt")
                with open(category_file, 'w') as f:
                    for item in self.findings[category]:
                        if isinstance(item, dict):
                            f.write(json.dumps(item, indent=2) + "\n\n")
                        else:
                            f.write(f"{item}\n")
    
    def print_summary(self):
        """Print a summary of findings"""
        print("\n===== FORENSIC ANALYSIS SUMMARY =====")
        print(f"PCAP File: {self.pcap_file}")
        print(f"URLs found: {len(self.findings['urls'])}")
        print(f"Email addresses: {len(self.findings['emails'])}")
        print(f"Potential credentials: {len(self.findings['credentials'])}")
        print(f"Authentication tokens: {len(self.findings['auth_tokens'])}")
        print(f"API keys: {len(self.findings['api_keys'])}")
        print(f"JWTs: {len(self.findings['jwts'])}")
        print(f"Sensitive numbers: {len(self.findings['sensitive_numbers'])}")
        print(f"HTTP requests: {len(self.findings['http_requests'])}")
        print(f"Unique connections: {len(self.findings['connections'])}")
        print(f"DNS queries: {len(self.findings['dns_queries'])}")
        print("====================================")

def start(pcap_dir, output_dir):
    # parser = argparse.ArgumentParser(description='Forensic analysis of PCAP files from Android devices')
    # parser.add_argument('pcap_file', help='Path to the PCAP file')
    # parser.add_argument('-o', '--output-dir', default='./forensic_output', help='Output directory for results')
    # parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    # args = parser.parse_args()
    
    for pcap_file in os.listdir(pcap_dir):
        pcap_file = pcap_dir + "/" + pcap_file
        analyzer = PcapAnalyzer(pcap_file, output_dir)
        analyzer.analyze_pcap()
