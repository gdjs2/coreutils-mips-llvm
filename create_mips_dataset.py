import os
import csv
import r2pipe
from tqdm import tqdm
from pathlib import Path
from loguru import logger
from argparse import ArgumentParser
from elftools.elf.elffile import ELFFile
from concurrent.futures import ProcessPoolExecutor, as_completed

STEP = 4

SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4

def sec_end_addr(s) -> int:
    '''
    Get the end address of a section.
    
    :param s: the section object
    :return: the end address of the section
    :rtype: int
    '''
    return s["sh_addr"] + s["sh_size"]

def generate_gt(file_path: str) -> tuple[list[int], list[list[int]], list[str], list[int]]:
    '''
    Generate ground truth for the given binary file.
    
    :param file_path: the path to the binary file
    :type file_path: str
    :return: a tuple containing lists of addresses, raw bytes, instructions, and ground truth labels
    :rtype: tuple[list[int], list[list[int]], list[str], list[int]]
    '''
    # The flags for eminate warning
    r2 = r2pipe.open(file_path, ["-e", "bin.relocs.apply=true"])

    # We only care about the sections will be loaded to main memory (with A flag). 
    main_memory_sections = []
    with open(file_path, "rb") as f:
        e = ELFFile(f)
        for s in e.iter_sections():
            if not (s["sh_flags"] & SHF_ALLOC):
                continue
            main_memory_sections.append(s)
    
    if not main_memory_sections: 
        raise RuntimeError(f"No section(s) in main memory.")
    # Sort the main memory sections by their mapping addresses
    main_memory_sections.sort(key=lambda s: s["sh_addr"])
    
    gt_list = []
    instr_list = []
    address_list = []
    bytes_list = []

    for section in main_memory_sections:
        for addr in range(section["sh_addr"], sec_end_addr(section), STEP):
            if not (section["sh_flags"] & SHF_EXECINSTR): # if non-executable section, all data
                gt_list.append(1)
            else:
                gt_list.append(0)

            # decoded instruction by radare2
            instr = r2.cmdj(f"pdj 1 @ {addr:#x}")
            if not instr or instr[0].get("type") == "invalid":
                instr = "invalid"
            else:
                instr = instr[0]["opcode"]
            instr_list.append(instr)

            # raw bytes
            raw_bytes = r2.cmdj(f"pxj 4 @ {addr:#x}")
            bytes_list.append(raw_bytes)

            # address
            address_list.append(addr)

    return address_list, bytes_list, instr_list, gt_list
        
def process_file(f: Path, output_file: Path) -> tuple[str, Exception | None]:
    '''
    Worker function to process a single file and generate its ground truth CSV.
    
    :param f: the input binary file path
    :type f: Path
    :param output_file: the output CSV file path
    :type output_file: Path
    :return: a tuple containing the file name and an exception if any occurred, otherwise None
    :rtype: tuple[str, Exception | None]
    '''
    try:
        address_list, bytes_list, instr_list, gt_list = generate_gt(str(f))
        hex_address_list = [f"0x{addr:x}" for addr in address_list]
        hex_bytes_list = [''.join(f'{b:02x}' for b in four_bytes) for four_bytes in bytes_list]

        with open(output_file, "w", newline='') as out_f:
            writer = csv.writer(out_f)
            writer.writerow(["address", "raw bytes", "instruction", "ground_truth"])
            writer.writerows(zip(hex_address_list, hex_bytes_list, instr_list, gt_list))
        
        return f.name, None
    except Exception as e:
        return f.name, e

if __name__ == "__main__":
    parser = ArgumentParser(description="Create MIPS dataset")
    parser.add_argument("--binary_dir", "-b", default="./build-output-mips/nonstripped/usr/local/bin", help="Directory to the non-stripped binary files of coreutils")
    parser.add_argument("--binary_file", "-f", help="Specific single binary file to process")
    parser.add_argument("--label_output_dir", "-o", default="./build-output-mips/labels", help="Directory to output the label files")
    parser.add_argument("--max_workers", "-j", type=int, help="Number of parallel workers")
    args = parser.parse_args()

    # Process a single file if specified
    if args.binary_file is not None:
        tqdm.write(f"Processing single file: {args.binary_file}")
        file_path = Path(args.binary_file)
        output_file_path = Path(args.label_output_dir) / f"{file_path.name}.csv"
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_name, error = process_file(file_path, output_file_path)
        if error is not None:
            tqdm.write(f"[ERROR] Error processing {file_name}: {error}")
        else:
            tqdm.write(f"Successfully processed {file_name}")
        exit(0)

    # Process all files in the specified directory
    binary_dir_path = Path(args.binary_dir)
    label_output_dir_path = Path(args.label_output_dir)
    label_output_dir_path.mkdir(parents=True, exist_ok=True)

    files = [f for f in binary_dir_path.glob("*") if f.is_file()]
    files_cnt = len(files)

    max_workers = args.max_workers if args.max_workers is not None else (max(os.cpu_count() - 1, 1) if os.cpu_count() else None) # type: ignore

    try:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future2file = {
                executor.submit(
                    process_file,
                    f,
                    label_output_dir_path / f"{f.name}.csv"
                ): f for f in files
            }

            for idx, future in enumerate(tqdm(as_completed(future2file), total=files_cnt, desc="Processing")):
                f = future2file[future]
                try:
                    file_name, error = future.result()
                    if error is not None:
                        tqdm.write(f"[ERROR] Error processing {file_name}: {error}")
                    else:
                        tqdm.write(f"[{idx+1}/{files_cnt}] Successfully processed {file_name}")

                except Exception as e:
                    tqdm.write(f"[EXCEPTION] Unhandled exception processing {f.name}: {e}")

    except KeyboardInterrupt:
        tqdm.write("Process interrupted by user. Cancelling remaining tasks...")
        for fut in future2file:
            fut.cancel()

        
    