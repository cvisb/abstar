#!/usr/bin/env python
# filename: germline_dbs.py

#
# Copyright (c) 2016 Bryan Briney
# License: The MIT license (http://opensource.org/licenses/MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software
# and associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#


from __future__ import print_function

from argparse import ArgumentParser
import os
import platform
import shutil
import subprocess as sp
import sys

from Bio import SeqIO



def parse_arguments():
    parser = ArgumentParser("Creates AbStar germline databases using an IMGT-gapped FASTA files of germline sequences. \
        Properly formatted germline sequence files can be obtained from: http://www.imgt.org/genedb/")
    parser.add_argument('-v', '--variable', dest='v', required=True,
                        help="Path to an IMGT-gapped, FASTA-formatted file containing Variable gene sequences. \
                        Sequences for both heavy and light chains should be included in a single file.")
    parser.add_argument('-d', '--diversity', dest='d', required=True,
                        help="Path to an IMGT-gapped, FASTA-formatted file containing Diversity gene sequences.")
    parser.add_argument('-j', '--joining', dest='j', required=True,
                        help="Path to an IMGT-gapped, FASTA-formatted file containing Joining gene sequences. \
                        Sequences for both heavy and light chains should be included in a single file.")
    parser.add_argument('-s', '--species', dest='species', required=True,
                        help="Name of the species from which the germline sequences are derived. \
                        If an AbStar germline database for the species already exists, it will be overwritten. \
                        Germline database names are converted to lowercase, so 'Human' and 'human' are equivalent. \
                        User-added germline databases will persist even after AbStar updates, so if you have added a \
                        'human' database and a new version of AbStar contains an updated 'human' database, the user-added \
                        database will still be used after the update.")
    parser.add_argument('-l', '--location', dest='db_location', default=None,
                        help="Location into which the new germline databases will be deposited. \
                        Default is '~/.abstar/'. \
                        Note that AbStar will only use user-generated databases found in '~/abstar/', \
                        so this option is provided primarily to test database creation without overwriting \
                        current databases of the same name. \
                        If the directory does not exist, it will be created.")
    parser.add_argument('-D', '--debug', dest="debug", action='store_true', default=False,
                        help="More verbose logging if set.")
    args = parser.parse_args()
    return args


# -------------------------
#
#    FILES/DIRECTORIES
#
# -------------------------


def get_addon_directory(db_location):
    if db_location is not None:
        print('\n')
        print('NOTE: You have selected a non-default location for the germline directory.')
        string = 'AbStar only looks in the default location (~/.abstar/) for user-created germline databases, '
        string += 'so this database will not be used by AbStar. The custom database location option is primarily '
        string += 'provided so that users can test the database creation process without overwriting existing databases.'
        print(string)
        addon_dir = db_location
    else:
        addon_dir = '~/.abstar'
    if not os.path.isdir(addon_dir):
        os.makedirs(addon_dir)
    return addon_dir


def get_binary_directory():
    mod_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bin_dir = os.path.join(mod_dir, 'assigners/bin')
    return bin_dir


def check_for_existing_db(addon_dir, species):
    dbs = [os.path.basename(d[0]) for d in os.walk(addon_dir)]
    if species.lower() in dbs:
        print('\n')
        print('WARNING: A {} germline database already exists.'.format(species.lower()))
        print('Creating a new database with that name will overwrite the old one.')
        keep_going = raw_input('Do you want to continue? [y/N]: ')
        if keep_going.upper() not in ['Y', 'YES']:
            print('')
            print('Aborting germline database creation.')
            print('\n')
            sys.exit()


def make_db_directories(addon_dir, species):
    species_dir = os.path.join(addon_dir, species.lower())
    if not os.path.isdir(species_dir):
        os.makedirs(species_dir)
    for db_name in ['imgt_gapped', 'ungapped', 'blast']:
        db_dir = os.path.join(species_dir, db_name)
        if os.path.isdir(db_dir):
            shutil.rmtree(db_dir)
        os.makedirs(db_dir)



# -------------------------
#
#    DATABASE CREATION
#
# -------------------------



def make_blast_db(ungapped_germline_file, addon_directory, segment, species):
    print('  - BLASTn')
    bin_dir = get_binary_directory()
    mbd_binary = os.path.join(bin_dir, 'makeblastdb_{}'.format(platform.system().lower()))
    mbd_output = os.path.join(addon_directory, '{}/blast/{}'.format(species.lower(), segment.lower()))
    mbd_log = os.path.join(addon_directory, '{}/blast/{}.blastlog'.format(species.lower(), segment.lower()))
    mbd_cmd = '{} -in {} -out {} -parse_seqids -dbtype nucl -logfile {}'.format(mbd_binary,
                                                                                ungapped_germline_file,
                                                                                mbd_output,
                                                                                mbd_log)
    p = sp.Popen(mbd_cmd, stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
    stdout, stderr = p.communicate()
    return mbd_output, stdout, stderr



def make_ungapped_db(ungapped_germline_file, addon_directory, segment, species):
    print('  - ungapped FASTA')
    output_file = os.path.join(addon_directory, '{}/ungapped/{}.fasta'.format(species.lower(), segment.lower()))
    seqs = SeqIO.parse(open(ungapped_germline_file), 'fasta')
    fastas = ['>{}\n{}'.format(s.description.split('|')[1], str(s.seq).replace('.', '')) for s in seqs]
    open(output_file, 'w').write('\n'.join(fastas))
    return output_file


def make_imgt_gapped_db(input_file, addon_directory, segment, species):
    print('  - IMGT-gapped FASTA')
    output_file = os.path.join(addon_directory, '{}/imgt_gapped/{}.fasta'.format(species.lower(), segment.lower()))
    seqs = sorted(list(SeqIO.parse(open(input_file), 'fasta')), key=lambda x: x.id)
    fastas = ['>{}\n{}'.format(s.description, str(s.seq)) for s in seqs]
    open(output_file, 'w').write('\n'.join(fastas))
    return output_file



# -------------------------
#
#        PRINTING
#
# -------------------------



def print_segment_info(segment, input_file):
    seqs = list(SeqIO.parse(open(input_file), 'fasta'))
    print('\n')
    seg_string = '  ' + segment.upper() + '  '
    print('-' * len(seg_string))
    print(seg_string)
    print('-' * len(seg_string))
    print(input_file)
    print('input file contains {} sequences'.format(len(seqs)))
    print('')
    print('Building germline databases:')



def main():
    args = parse_arguments()
    addon_dir = get_addon_directory(args.db_location)
    check_for_existing_db(addon_dir, args.species)
    make_db_directories(addon_dir, args.species)
    for segment, infile in [('Variable', args.v), ('Diversity', args.d), ('Joining', args.j)]:
        print_segment_info(segment, infile)
        imgt_gapped_file = make_imgt_gapped_db(infile, addon_dir, segment[0].lower(), args.species)
        ungapped_file = make_ungapped_db(imgt_gapped_file, addon_dir, segment[0].lower(), args.species)
        blast_file, stdout, stderr = make_blast_db(ungapped_file, addon_dir, segment[0].lower(), args.species)
        if args.debug:
            print(stdout)
            print(stderr)
    print('\n')


if __name__ == '__main__':
    # args = parse_arguments()
    main()
