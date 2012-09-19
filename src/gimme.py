'''
    Gimme: a transcripts assembler based on alignments.

    Copyright (C) 2012 Michigan State University

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Contact: Likit Preeyanon, preeyano@msu.edu
'''
#!/usr/bin/env python

import sys, csv
import argparse
from sys import stderr, stdout

import networkx as nx
from utils import pslparser, get_min_path


GAP_SIZE = 10 # a minimum intron size (bp)
MAX_INTRON = 100000 # a maximum intron size (bp)
MIN_UTR = 100 # a minimum UTR size (bp)
MIN_EXON = 10 # a minimum exon size (bp)
MIN_TRANSCRIPT_LEN = 300 # a minimum transcript length (bp)

exon_db = {}
intron_db = {}
clusters = {}

class ExonObj:
    def __init__(self, chrom, start, end):
        self.chrom = chrom
        self.start = start
        self.end = end
        self.terminal = None
        self.next_exons = set([])
        self.introns = set([])
        self.single = False

    def __str__(self):
        return '%s:%d-%d' % (self.chrom, self.start, self.end)


def parse_bed(bed_file, min_exon=MIN_EXON):
    '''Reads alignments from BED format and creates
    exon objects from a transcript.

    '''
    reader = csv.reader(bed_file, dialect='excel-tab')
    for row in reader:
        exons = []
        chrom = row[0]
        chrom_start = int(row[1])

        exon_sizes = [int(s) for s in row[10].split(',')]
        exon_starts = [chrom_start + int(s) for s in row[11].split(',')]

        for i in range(len(exon_starts)):
            exon_start = exon_starts[i]
            exon_end = exon_start + exon_sizes[i]

            exon = ExonObj(chrom, exon_start, exon_end)
            exons.append(exon)

        exons = delete_gap(exons)

        for kept_exons in remove_small_exon(exons, min_exon):
            yield kept_exons


def parse_psl(psl_file, min_exon=MIN_EXON):
    '''Reads alignments from PSL format and creates
    exon objects from each transcript.

    '''
    for pslobj in pslparser.read(psl_file):
        exons = []

        for i in range(len(pslobj.attrib['tStarts'])):
            exon_start = pslobj.attrib['tStarts'][i]
            exon_end = exon_start + pslobj.attrib['block_sizes'][i]

            exon = ExonObj(pslobj.attrib['tName'], exon_start, exon_end)
            exons.append(exon)

        exons = delete_gap(exons)

        for kept_exons in remove_small_exon(exons, min_exon):
            yield kept_exons


def remove_small_exon(exons, min_exon):
    '''Removes a small exon and a transcript is split into
    parts that precedes and succeeds the exon.

    '''
    kept = []

    for exon in exons:
        if (exon.end - exon.start) + 1 >= min_exon:
            kept.append(exon)
        else:
            if kept:
                yield kept
                kept = []
    if kept:
        yield kept


def add_introns(exons, intron_db, exon_db,
                clusters, cluster_no):
    '''Get introns from a set of exons.'''

    existing_clusters = set([])

    introns = []

    for i in range(len(exons)):
        curr_exon = exon_db[str(exons[i])]
        try:
            next_exon = exon_db[str(exons[i + 1])]
        except IndexError:
            pass
        else:
            intron_start = curr_exon.end + 1
            intron_end = next_exon.start - 1

            if intron_end - intron_start > MAX_INTRON:
                continue

            curr_exon.next_exons.add(str(next_exon))

            intron_name = '%s:%d-%d' % (curr_exon.chrom,
                                            intron_start,
                                            intron_end)
            intron = nx.DiGraph(name=intron_name, cluster=None)

            try:
                intron_ = intron_db[intron.graph['name']]
            except KeyError:
                intron_db[intron.graph['name']] = intron
                intron.add_edge(str(curr_exon), str(next_exon))
                introns.append(intron)

                curr_exon.introns.add(intron.graph['name'])
                next_exon.introns.add(intron.graph['name'])
            else:
                intron_.add_edge(str(curr_exon), str(next_exon))
                introns.append(intron_)
                existing_clusters.add(intron_.graph['cluster'])

                curr_exon.introns.add(intron_.graph['name'])
                next_exon.introns.add(intron_.graph['name'])

    if introns:
        if not existing_clusters:
            cluster = nx.DiGraph()
            if len(introns) > 1:
                cluster.add_path([i.graph['name'] for i in introns])
                for intron in introns:
                    intron.graph['cluster'] = cluster_no
            else:
                cluster.add_node(introns[0].graph['name'])
                introns[0].graph['cluster'] = cluster_no

        else:
            cluster = nx.DiGraph(exons=set([]))
            for cl in existing_clusters:
                cluster.add_edges_from(clusters[cl].edges())
                clusters.pop(cl)

            for intron in cluster.nodes():
                intron_db[intron].graph['cluster'] = cluster_no

            if len(introns) > 1:
                cluster.add_path([i.graph['name'] for i in introns])

                for intron in introns:
                    intron.graph['cluster'] = cluster_no
            else:
                cluster.add_node(introns[0].graph['name'])
                introns[0].graph['cluster'] = cluster_no

        clusters[cluster_no] = cluster

    return cluster_no


def collapse_exons(g, exon_db):
    # g = an exon graph.

    exons = [exon_db[e] for e in g.nodes()]
    sorted_exons = sorted(exons, key=lambda x: (x.end, x.start))

    i = 0
    curr_exon = sorted_exons[i]
    while i <= len(sorted_exons):
        try:
            next_exon = sorted_exons[i + 1]
        except IndexError:
            pass
        else:
            if curr_exon.end == next_exon.end:
                if next_exon.terminal == 1:
                    g.add_edges_from([(str(curr_exon), n)\
                            for n in g.successors(str(next_exon))])
                    g.remove_node(str(next_exon))
                else:
                    if curr_exon.terminal == 1:
                        if next_exon.start - curr_exon.start <= MIN_UTR:
                            g.add_edges_from([(str(next_exon), n)\
                                    for n in g.successors(str(curr_exon))])
                            g.remove_node(str(curr_exon))

                    curr_exon = next_exon
            else:
                curr_exon = next_exon
        i += 1

    i = 0
    exons = [exon_db[e] for e in g.nodes()]
    sorted_exons = sorted(exons, key=lambda x: (x.start, x.end))
    curr_exon = sorted_exons[0]
    while i <= len(sorted_exons):
        try:
            next_exon = sorted_exons[i + 1]
        except IndexError:
            pass
        else:
            if curr_exon.start == next_exon.start:
                if curr_exon.terminal == 2:
                    g.add_edges_from([(n, str(next_exon))\
                            for n in g.predecessors(str(curr_exon))])
                    g.remove_node(str(curr_exon))
                    curr_exon = next_exon
                else:
                    if next_exon.terminal == 2:
                        if next_exon.end - curr_exon.end <= MIN_UTR:
                            g.add_edges_from([(n, str(curr_exon))\
                                    for n in g.predecessors(str(next_exon))])
                            g.remove_node(str(next_exon))
                        else:
                            curr_exon = next_exon
                    else:
                        curr_exon = next_exon
            else:
                curr_exon = next_exon
        i += 1


def delete_gap(exons):
    '''Alignments may contain small gaps from indels and etc.

    The program fills up gaps to obtain a complete exon.

    A maximum size of a gap can be adjusted by assigning a new
    value to GAP_SIZE parameter on a command line.

    '''

    i = 0
    new_exons = []
    curr_exon = exons[i]

    while True:
        try:
            next_exon = exons[i + 1]
        except IndexError:
            break
        else:
            if next_exon.start - curr_exon.end <= GAP_SIZE:
                curr_exon.end = next_exon.end
            else:
                new_exons.append(curr_exon)
                curr_exon = next_exon
        i += 1

    new_exons.append(curr_exon)

    return new_exons


def add_exon(db, exons):
    '''1.Change a terminal attribute of a leftmost exon
    and a rightmost exon to 1 and 2 respectively.

    A terminal attribute has a value 'None' by default.

    2.Add exons to the exon database (db).

    '''
    exons[0].terminal = 1
    exons[-1].terminal = 2

    for exon in exons:
        try:
            exon_ = db[str(exon)]
        except KeyError:
            db[str(exon)] = exon
        else:
            if not exon.terminal and exon_.terminal:
                exon_.terminal = None


def merge_clusters(exon_db):
    big_cluster = nx.Graph()
    for exon in exon_db.itervalues():
        path = []
        for intron in exon.introns:
            path.append(intron_db[intron].graph['cluster'])

        if len(path) > 1:
            big_cluster.add_path(path)
        elif len(path) == 1:
            big_cluster.add_node(path[0])
        else:
            pass

    return big_cluster


def walk_down(intron_coord, path, all_paths, cluster):
    '''Returns all downstream exons from a given exon.'''

    if cluster.successors(intron_coord) == []:
        all_paths.append(path[:])
        return
    else:
        for nex in cluster.successors(intron_coord):
            if nex not in path:
                path.append(nex)

            walk_down(nex, path, all_paths, cluster)

            path.pop()


def get_path(cluster):
    '''Returns all paths from a given cluster.'''

    roots = [node for node in cluster.nodes() \
                    if not cluster.predecessors(node)]
    all_paths = []

    for root in roots:
        path = [root]
        walk_down(root, path, all_paths, cluster)

    return all_paths


def build_splice_graph(cluster, intron_db, exon_db, merged_exons):
    '''Return a directed graph containing all exons.'''

    all_paths = get_path(cluster)

    G = nx.DiGraph()
    for path in all_paths:
        for intron_coord in path:
            intron = intron_db[intron_coord]
            for exon in intron.exons:
                for next_exon in exon_db[exon].next_exons:
                    if next_exon not in merged_exons:
                        G.add_edge(exon, next_exon)

    return G


<<<<<<< HEAD
def checkCriteria(transcript):
    '''Return True or False whether a transcript pass or
    fail the criteria.

    '''

    exons = sorted([exonDb[e] for e in transcript],
=======
def check_criteria(transcript):
    exons = sorted([exon_db[e] for e in transcript],
>>>>>>> get_min_trial
                            key=lambda x: (x.start, x.end))

    transcript_length = sum([exon.end - exon.start for exon in exons])
    if transcript_length <= MIN_TRANSCRIPT_LEN:
        return False # fail
    else:
        return True # pass


def print_bed_graph(transcript, gene_id, tran_id):
    '''Print a splice graph in BED format.'''

    exons = sorted([exon_db[e] for e in transcript],
                            key=lambda x: (x.start, x.end))

    chrom_start = exons[0].start
    chrom_end = exons[-1].end
    chrom = exons[0].chrom

    block_starts = ','.join([str(exon.start - chrom_start) for exon in exons])
    block_sizes = ','.join([str(exon.end - exon.start) for exon in exons])

    name = '%s:%d.%d' % (chrom, gene_id, tran_id)
    score = 1000
    item_RGB = '0,0,0'
    thick_start = chrom_start
    thick_end = chrom_end
    strand = '+'
    block_count = len(exons)

    writer = csv.writer(stdout, dialect='excel-tab')
    writer.writerow((chrom,
                    chrom_start,
                    chrom_end,
                    name,
                    score,
                    strand,
                    thick_start,
                    thick_end,
                    item_RGB,
                    block_count,
                    block_sizes,
                    block_starts))

def print_bed_graph_single(exon, gene_id, tran_id):
    '''Print a splice graph in BED format.'''

    chrom_start = exon.start
    chrom_end = exon.end
    chrom = exon.chrom

    block_starts = ','.join([str(exon.start - chrom_start)])
    block_sizes = ','.join([str(exon.end - exon.start)])

    name = '%s:%d.%d' % (chrom, gene_id, tran_id)
    score = 1000
    item_RGB = '0,0,0'
    thick_start = chrom_start
    thick_end = chrom_end
    strand = '+'
    block_count = 1

    writer = csv.writer(stdout, dialect='excel-tab')
    writer.writerow((chrom,
                    chrom_start,
                    chrom_end,
                    name,
                    score,
                    strand,
                    thick_start,
                    thick_end,
                    item_RGB,
                    block_count,
                    block_sizes,
                    block_starts))

def build_gene_models(exon_db, intron_db, clusters,
                            big_cluster, is_min=False):
    print >> stderr, 'Building gene models...'

    removed_clusters = set([])
    transcripts_num = 0
    gene_id = 0
    excluded = 0

    for cl_num, cl in enumerate(big_cluster.nodes(), start=1):
        if cl not in removed_clusters:
            g = nx.DiGraph()
            for intron in clusters[cl].nodes():
                g.add_edges_from(intron_db[intron].edges())

            for neighbor in big_cluster.neighbors(cl):
                if neighbor != cl: # chances are node connects to itself.
                    neighbor_cluster = clusters[neighbor]
                    for intron in neighbor_cluster.nodes():
                        g.add_edges_from(intron_db[intron].edges())

                removed_clusters.add(neighbor)
            removed_clusters.add(cl)

            if g.nodes():
                gene_id += 1
                trans_id = 0
                collapse_exons(g, exon_db)
                if not is_min:
                    for transcript in get_path(g):
                        if check_criteria(transcript):
                            trans_id += 1
                            transcripts_num += 1
                            print_bed_graph(transcript, gene_id, trans_id)
                        else:
                            excluded += 1

                else:
                    max_paths = get_path(g)
                    paths = []
                    for pth in max_paths:
                        paths.append(get_min_path.getEdges(pth))

                    for transcript in get_min_path.getMinPaths(paths):
                        if check_criteria(transcript):
                            transcripts_num += 1
                            trans_id += 1
                            print_bed_graph(transcript, gene_id, trans_id)
                        else:
                            excluded += 1
            if trans_id == 0:
                gene_id -= 1

        if cl_num % 1000 == 0:
            print >> stderr, \
                    '...', cl_num, ': excluded', excluded, 'transcript(s)'

    return gene_id, transcripts_num


def merge_exons(exons):
    for chrom in exons:
        exons[chrom] = sorted(exons[chrom], key=lambda x: x.start)
    
    new_exons = {}

    for chrom in exons:
        i = 0
        new_exons[chrom] = []
        curr_exon = exons[chrom][i]
        while i < (len(exons[chrom])):
            try:
                next_exon = exons[chrom][i+1]
            except IndexError:
                return new_exons
            else:
                if next_exon.start <= curr_exon.end:
                    if next_exon.end > curr_exon.end:
                        next_exon.start = curr_exon.start
                        curr_exon = next_exon
                else:
                    new_exons[chrom].append(curr_exon)
                    curr_exon = next_exon
            i += 1

<<<<<<< HEAD
    return new_exons

def detect_format(inputFile):
    fp = open(inputFile)
=======

def detect_format(input_file):
    fp = open(input_file)
>>>>>>> get_min_trial
    cols = fp.readline().split()
    fp.close()

    if len(cols) == 21:
        if int(cols[11]) <= int(cols[12]) and cols[8] in ['+', '.', '-']:
            return 'PSL'
    elif len(cols) == 12:
        if int(cols[1]) <= int(cols[2]) and cols[5] in ['+', '.', '-']:
            return 'BED'
    else:
        return None

def main(input_files):
    cluster_no = 0
    single_exons = {}

    for input_file in input_files:
        input_format = detect_format(input_file)
        if input_format == 'PSL':
            parse = parse_psl
        elif input_format == 'BED':
            parse = parse_bed
        else:
            print >> stderr, 'ERROR: Unrecognized input format. ' + \
                    'Use utils/gff2bed.py to convert GFF to BED.'
            raise SystemExit

        print >> stderr, 'Parsing alignments from %s...' % input_file
        for n, exons in enumerate(parse(open(input_file)), start=1):
            if len(exons) > 1:
                add_exon(exon_db, exons)
                add_introns(exons, intron_db, exon_db, clusters, cluster_no)
                cluster_no += 1
            else:
                if exons[0].chrom not in single_exons:
                    single_exons[exons[0].chrom] = [exons[0]]
                else:
                    single_exons[exons[0].chrom].append(exons[0])

            if n % 1000 == 0:
                print >> stderr, '...', n

    big_cluster = merge_clusters(exon_db)
    gene_id, transcripts_num = build_gene_models(exon_db,
                                    intron_db, clusters,
                                    big_cluster, args.min)

    merged_single_exons = merge_exons(single_exons)

    for chrom in merged_single_exons:
        for exon in merged_single_exons[chrom]:
            gene_id += 1
            transcripts_num += 1
            print_bed_graph_single(exon, gene_id, 1)


    print >> stderr, '\nTotal exons = %d' % len(exon_db)
    print >> stderr, 'Total genes = %d' % gene_id
    print >> stderr, 'Total transcripts = %d' % (transcripts_num)
    print >> stderr, 'Isoform/gene = %.2f' % (float(transcripts_num)
                                                / len(clusters))


if __name__=='__main__':
    parser = argparse.ArgumentParser(prog='Gimme')
    parser.add_argument('--MIN_UTR', type=int, default=MIN_UTR,
        help='a cutoff size of alternative UTRs (bp) (default: %(default)s)')
    parser.add_argument('--GAP_SIZE', type=int, default=GAP_SIZE,
        help='a maximum gap size (bp) (default: %(default)s)')
    parser.add_argument('--MAX_INTRON', type=int, default=MAX_INTRON,
        help='a maximum intron size (bp) (default: %(default)s)')
    parser.add_argument('--MIN_TRANSCRIPT_LEN', type=int,
        default=MIN_TRANSCRIPT_LEN,
        help='a minimum size of transcript (bp) (default: %(default)s)')
    parser.add_argument('--min', action='store_true',
        help='report a minimum set of isoforms')
    parser.add_argument('input', type=str, nargs='+',
        help='input file(s) in PSL/BED format')
    parser.add_argument('--version', action='version',
                        version='%(prog)s version 0.9')

    args = parser.parse_args()
    if args.MIN_UTR <=0:
        raise SystemExit, 'Invalid UTRs size (<=0)'
    elif args.MIN_UTR != MIN_UTR:
        MIN_UTR = args.MIN_UTR
        print >> sys.stderr, 'User defined MIN_UTR = %d' % MIN_UTR
    else:
        print >> sys.stderr, 'Default MIN_UTR = %d' % MIN_UTR

    if args.GAP_SIZE < 0:
        raise SystemExit, 'Invalid intron size (<0)'
    elif args.GAP_SIZE != GAP_SIZE:
        GAP_SIZE = args.GAP_SIZE
        print >> sys.stderr, 'User defined GAP_SIZE = %d' % GAP_SIZE
    else:
        print >> sys.stderr, 'Default GAP_SIZE = %d' % GAP_SIZE

    if args.MAX_INTRON <= 0:
        raise SystemExit, 'Invalid intron size (<=0)'
    elif args.MAX_INTRON != MAX_INTRON:
        MAX_INTRON = args.MAX_INTRON
        print >> sys.stderr, 'User defined MAX_INTRON = %d' % MAX_INTRON
    else:
        print >> sys.stderr, 'Default MAX_INTRON = %d' % MAX_INTRON

    if args.MIN_TRANSCRIPT_LEN <= 0:
        raise SystemExit, 'Invalid transcript size (<=0)'
    elif args.MIN_TRANSCRIPT_LEN != MIN_TRANSCRIPT_LEN:
        MIN_TRANSCRIPT_LEN = args.MIN_TRANSCRIPT_LEN
        print >> sys.stderr, 'User defined MIN_TRANSCRIPT_LEN = %d' % \
                                                    MIN_TRANSCRIPT_LEN
    else:
        print >> sys.stderr, 'Default MIN_TRANSCRIPT_LEN = %d' % \
                                                    MIN_TRANSCRIPT_LEN

    if args.min:
        print >> sys.stderr, 'Search for a minimum set of isoforms = yes'
    else:
        print >> sys.stderr, 'Search for a maximum set of isoforms = yes'

    if args.input:
        main(args.input)
