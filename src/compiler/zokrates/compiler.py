import os
import re
import json
from shutil import copy, rmtree
from subprocess import SubprocessError
from typing import List

import my_logging
from utils.run_command import run_command
from utils.helpers import read_file, prepend_to_lines, save_to_file, lines_of_code

# get relevant paths
from utils.timer import time_measure

script_dir = os.path.dirname(os.path.realpath(__file__))
# could also be a path
zok_bin = os.path.join(os.environ['ZOKRATES_ROOT'], 'zokrates')


verify_libs_filename = 'verify_libs.sol'
verify_libs_template = os.path.join(script_dir, verify_libs_filename)
verify_libs_code = read_file(verify_libs_template)


# g16 proof verification: >6 Mio gas for 2 public inputs
# pghr13 proof verification: 1.6Mio gas for 2 public inputs
# gm17 proof verification: 0.9Mio gas for 2 public inputs
default_proving_scheme = 'gm17'
n_proof_arguments = 8


def get_work_dir(output_directory: str, name: str):
	return os.path.join(output_directory, name + '_zok')


def compile_zokrates(code: str, output_directory: str, name='Verifier', scheme=default_proving_scheme):
	try:
		work_dir = get_work_dir(output_directory, name)
		if os.path.isdir(work_dir):
			rmtree(work_dir)
		os.mkdir(work_dir)

		# create file holding code
		code_file_name = f'{name}.code'
		code_file = os.path.join(work_dir, code_file_name)
		with open(code_file, "w+") as f:
			f.write(code)

		with time_measure('compileZokrates'):
			# compile
			try:
				run_command([zok_bin, 'compile', '-i', code_file_name, '--light'], cwd=work_dir)
			except SubprocessError as e:
				raise ValueError(f'Error compiling {code_file}:\n{code}') from e

			# setup
			run_command([zok_bin, 'setup', '--proving-scheme', scheme], cwd=work_dir)

			# export verifier
			run_command([zok_bin, 'export-verifier', '--proving-scheme', scheme], cwd=work_dir)

		verifier_contract_file = os.path.join(work_dir, 'verifier.sol')
		verifier_contract = read_file(verifier_contract_file)

		# beatify output
		verifier_contract = prepend_to_lines(code, '// ') + '\n\n' + verifier_contract

		# rename contract
		verifier_contract = verifier_contract.replace('contract Verifier', f'contract {name}')

		# extract libraries to separate file
		verifier_contract = extract_libraries(output_directory, verifier_contract)

		# add wrapper
		verifier_contract = add_wrapper(verifier_contract)

		# record lines of code
		my_logging.data('verifierLoc', lines_of_code(verifier_contract))

		# save
		output_filename = f'{name}_verifier.sol'
		save_to_file(output_directory, output_filename, verifier_contract)

		return output_filename, work_dir

	except SubprocessError as e:
		print(e)
		raise ValueError('Error compiling:\n' + code) from e


def generate_proof(zokrates_directory: str, args: List[int], scheme=default_proving_scheme):
	try:
		args = [str(a) for a in args]

		run_command([zok_bin, 'compute-witness', '-a'] + args, zokrates_directory)

		run_command([zok_bin, 'generate-proof', '--proving-scheme', scheme], zokrates_directory)

		proof_file = os.path.join(zokrates_directory, 'proof.json')
		proof = read_file(proof_file)

		proof = clean_json(proof)

		return json.loads(proof)
	except SubprocessError as e:
		raise ValueError(f'Could not generate proof for {zokrates_directory} using {args}') from e


def extract_libraries(output_directory: str, verifier_contract: str):
	# move libraries into separate file
	# copy(verify_libs_template, output_directory)
	libs_import = f'pragma solidity ^0.4.0;\nimport "./{verify_libs_filename}";\n'
	if verify_libs_code not in verifier_contract:
		raise ValueError('Could not find library code solidity file generated by zokrates')
	verify_libs_code_4 = verify_libs_code.replace('pragma solidity ^0.5.0;', 'pragma solidity ^0.4.0;')
	save_to_file(output_directory, verify_libs_filename, verify_libs_code_4)
	return verifier_contract.replace(verify_libs_code, libs_import)


verify_wrapper = """
	function check_verify(uint[{}] memory proof, uint[{}] memory input) public{{
		require(verifyTx(
		[proof[0], proof[1]],
		[[proof[2], proof[3]], [proof[4], proof[5]]],
		[proof[6], proof[7]],
		input));
	}}
"""


def add_wrapper(verifier_contract: str):
	verify_signature = "function verifyTx\\(([^)]*)\\)"
	m = re.search(verify_signature, verifier_contract)
	params = m.group(1)
	m2 = re.search(r'uint\[([0-9]*)\] memory input', params)
	n_inputs = m2.group(1)

	add = verify_wrapper.format(n_proof_arguments, n_inputs)

	verifier_contract = replace_last(verifier_contract, '\n}', add + '\n}')
	return verifier_contract


def replace_last(s: str, pattern: str, new: str):
	parts = s.rsplit(pattern, 1)
	return new.join(parts)


def clean_json(s):
	# handle leading zeroes in integers (including hex representations):
	# 010 -> "010"
	# 01a -> "01a"
	s = re.sub(r'([^0-9])(0[0-9a-fA-F]*)(?=[,\]])', r'\1"\2"', s)

	# handle trailing commas
	s = re.sub(",[ \t\r\n]+}", "}", s)
	s = re.sub(",[ \t\r\n]+\]", "]", s)

	return s
