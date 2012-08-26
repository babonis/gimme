'''This script reads a gene model from BED file
and writes a DNA sequence to standard output.
The script requires pygr package.

'''

import sys
import csv

from collections import namedtuple
from pygr import seqdb, sequtil

Exon = namedtuple('Exon', 'chrom, start, end')

def get_sequence_transcript(genome, exons):
    seq = ''
    for exon in exons:
        s = genome[exon.chrom][exon.start:exon.end]
        seq += str(s)

    return seq

def get_sequence_exon(genome, exons):
    seqs = []
    for exon in exons:
        s = genome[exon.chrom][exon.start:exon.end]
        seqs.append(str(s))

    return seqs

def write_seq(filename, genome, output):
    reader = csv.reader(open(filename), dialect='excel-tab')

    for n, line in enumerate(reader, start=1):
        chrom = line[0]
        chrom_start = int(line[1])
        gene_id = line[3]
        exon_starts = [int(start) + chrom_start for start in line[-1].split(',')]
        exon_sizes = [int(size) for size in line[-2].split(',')]
        exon_ends = [exon_starts[i] + exon_sizes[i] for i in range(len(exon_starts))]
        exons = [Exon(chrom, exon_starts[i], exon_ends[i]) for i in \
                range(len(exon_starts))]

        if (output == 'default'
                or output == 'transcript'):
            seq = get_sequence_transcript(genome, exons)
            sequtil.write_fasta(sys.stdout, seq, id=gene_id)
        elif output == 'exon':
            seqs = get_sequence_exon(genome, exons)

            for n, seq in enumerate(seqs, start=1):
                seq_id = gene_id + '_' + str(n)
                sequtil.write_fasta(sys.stdout, seq, id=seq_id)
        else:
            print >> sys.stderr, 'Unsupported output format.'
            raise SystemExit

        if n % 1000 == 0: print >> sys.stderr, '...', n

if __name__=='__main__':
    filename = sys.argv[1]
    genome_file = sys.argv[2]
    try:
        output = sys.argv[3]
    except IndexError:
        output = 'default'

    genome = seqdb.SequenceFileDB(genome_file, verbose=False)
    write_seq(filename, genome, output)
