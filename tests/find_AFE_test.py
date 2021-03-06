import unittest

import networkx as nx
from utils.find_AFE import Exon, find_AFE


# class TestLoadData(unittest.TestCase):
#     def test_load_data(self):
#         for exons, transcript_id in get_exon_node(test_file):
#             pass
#         self.assertTrue(len(exons) > 1)


# class TestExonGraph(unittest.TestCase):
#     def test_build_exon_graph(self):
#         for exons, transcript_id in get_exon_node(test_file):
#             self.graph = nx.DiGraph()
#             self.graph.add_path([str(e) for e in exons])
#             self.assertEqual(len(exons), len(self.graph.nodes()))

def get_num_exons(paths):
    num_exons = []
    for path in paths:
        for exons in path:
            num_exons.append(len(exons))

    return num_exons


class TestFindAFEPositive(unittest.TestCase):
    def setUp(self):
        self.exonsDB = {}
        self.graph = nx.DiGraph()
        self.ex1 = Exon('chrX', 1000, 2000, 'ex1.1', '+')
        self.ex2 = Exon('chrX', 3000, 4000, 'ex1.1', '+')
        self.ex3 = Exon('chrX', 5000, 6000, 'ex1.1', '+')
        self.ex4 = Exon('chrX', 800, 900, 'ex1.1', '+')
        self.ex5 = Exon('chrX', 1500, 2500, 'ex1.1', '+')
        self.exonsDB[str(self.ex1)] = self.ex1
        self.exonsDB[str(self.ex2)] = self.ex2
        self.exonsDB[str(self.ex3)] = self.ex3
        self.exonsDB[str(self.ex4)] = self.ex4
        self.exonsDB[str(self.ex5)] = self.ex5

    def test_positive_on_AFE(self):
        '''
            []------[]
            []------[]
        '''

        self.graph.add_path(['start', str(self.ex1),
                                    str(self.ex2), 'end'])
        self.transcripts = [[str(self.ex1), str(self.ex2)]]
        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 0)

    def test_positive_two_path_one_exon(self):
        '''
            []------->[]
            []---->[]
        '''

        path1 = ['start', str(self.ex1), str(self.ex2), 'end']
        path2 = ['start', str(self.ex5), str(self.ex2), 'end']
        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.transcripts = [path1, path2]
        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 2)
        self.assertItemsEqual(get_num_exons(paths), [2, 2])

    def test_positive_no_AFE_with_ALE(self):
        '''
            []--------->[]--------->[]
            []--------->[]----->[]
        '''

        path1 = ['start', str(self.ex1), str(self.ex5),
                   str(self.ex3), 'end']
        path2 = ['start', str(self.ex1), str(self.ex5),
                   str(self.ex2), 'end']

        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.transcripts = [path1, path2]
        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 0)

    def test_positive_single_AFE_with_ALE(self):
        '''
               []------>[]--------->[]
            [*]-------->[]----->[]
        '''

        path1 = ['start', str(self.ex1), str(self.ex5),
                   str(self.ex3), 'end']
        path2 = ['start', str(self.ex4), str(self.ex5),
                   str(self.ex2), 'end']

        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.transcripts = [path1, path2]
        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 2)
        self.assertItemsEqual(get_num_exons(paths), [2, 2])

    def test_positive_two_path_two_exon(self):
        '''
            []------------>[]---------->[]
              [*]--->[*]-->[]---------->[]
        '''
        self.ex6 = Exon('chrX', 7000, 8000, 'ex1.1', '+')
        self.exonsDB[str(self.ex6)] = self.ex6
        path1 = ['start', str(self.ex1),
                    str(self.ex3), str(self.ex6), 'end']
        path2 = ['start', str(self.ex5), str(self.ex2),
                    str(self.ex3), str(self.ex6), 'end']
        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.transcripts = [path1, path2]

        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 2)
        self.assertItemsEqual(get_num_exons(paths), [2, 3])

    def test_positive_two_path_multiple_exon(self):
        '''
            []-------->[]------->[]------->[]
                [*]----------------------->[]
        '''

        self.ex6 = Exon('chrX', 7000, 8000, 'ex1.1', '+')
        self.ex7 = Exon('chrX', 9000, 10000, 'ex1.1', '+')
        self.exonsDB[str(self.ex6)] = self.ex6
        self.exonsDB[str(self.ex7)] = self.ex7

        path1 = ['start', str(self.ex1), str(self.ex3),
                    str(self.ex6), str(self.ex7), 'end']
        path2 = ['start', str(self.ex5), str(self.ex7), 'end']
        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.transcripts = [path1, path2]

        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 2)
        self.assertItemsEqual(get_num_exons(paths), [4, 2])

    def test_positive_three_path_one_exon(self):
        '''
             [*]------->[]
                [*]---->[]
            [*]-------->[]
        '''

        path1 = ['start', str(self.ex1), str(self.ex2), 'end']
        path2 = ['start', str(self.ex5), str(self.ex2), 'end']
        path3 = ['start', str(self.ex4), str(self.ex2), 'end']
        self.transcripts = [path1, path2, path3]
        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.graph.add_path(path3)

        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 3)
        self.assertItemsEqual(get_num_exons(paths), [2, 2, 2])

    # def test_positive_three_path_two_exon(self):
    #     '''
    #         [*]---->[*]----->[]
    #           [*]---->[*]--->[]
    #          [*]--->[*]----->[]
    #     '''

    #     self.ex4 = Exon('chrX', 700, 800, 'ex1.1', '+')
    #     self.ex6 = Exon('chrX', 500, 600, 'ex1.1', '+')
    #     self.ex8 = Exon('chrX', 3500, 4500, 'ex1.1', '+')
    #     self.exonsDB[str(self.ex4)] = self.ex4
    #     self.exonsDB[str(self.ex6)] = self.ex6
    #     self.exonsDB[str(self.ex8)] = self.ex8

    #     path1 = ['start', str(self.ex1),
    #                 str(self.ex2), str(self.ex3), 'end']
    #     path2 = ['start', str(self.ex5),
    #                 str(self.ex8), str(self.ex3), 'end']
    #     path3 = ['start', str(self.ex6),
    #                 str(self.ex4), str(self.ex3), 'end']
    #     self.transcripts = [path1, path2, path3]

    #     self.graph.add_path(path1)
    #     self.graph.add_path(path2)
    #     self.graph.add_path(path3)

    #     paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))
    #     import sys
    #     print >> sys.stderr, paths

    #     self.assertEqual(len(paths[0]), 3)
    #     self.assertItemsEqual(get_num_exons(paths), [3, 3, 3])


class TestFindAFENegative(unittest.TestCase):
    def setUp(self):
        self.exonsDB = {}
        self.graph = nx.DiGraph()
        self.ex1 = Exon('chrX', 1000, 2000, 'ex1.1', '-')
        self.ex2 = Exon('chrX', 3000, 4000, 'ex1.1', '-')
        self.ex3 = Exon('chrX', 5000, 6000, 'ex1.1', '-')
        self.ex4 = Exon('chrX', 800, 900, 'ex1.1', '-')
        self.ex5 = Exon('chrX', 1500, 2500, 'ex1.1', '-')
        self.exonsDB[str(self.ex1)] = self.ex1
        self.exonsDB[str(self.ex2)] = self.ex2
        self.exonsDB[str(self.ex3)] = self.ex3
        self.exonsDB[str(self.ex4)] = self.ex4
        self.exonsDB[str(self.ex5)] = self.ex5

    def test_negative_no_AFE_with_ALE(self):
        '''
            []<-----[]<----[]<-----[]
               []<---------[]<-----[]
        '''

        path1 = (['end', str(self.ex4), str(self.ex1),
                    str(self.ex2), str(self.ex3), 'start'])
        path2 = (['end', str(self.ex5),
                    str(self.ex2), str(self.ex3), 'start'])

        path1.reverse()
        path2.reverse()

        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.transcripts = [path1, path2]
        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 0)

    def test_negative_single_AFE_with_ALE(self):
        '''
               []<-------[]<-------[]
                  []<----[]<----------[*]
        '''

        self.ex6 = Exon('chrX', 7000, 8000, 'ex1.1', '-')
        self.exonsDB[str(self.ex6)] = self.ex6

        path1 = (['end', str(self.ex1), str(self.ex2),
                    str(self.ex3), 'start'])
        path2 = (['end', str(self.ex4),
                    str(self.ex2), str(self.ex6), 'start'])

        path1.reverse()
        path2.reverse()

        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.transcripts = [path1, path2]
        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 2)
        self.assertItemsEqual(get_num_exons(paths), [2, 2])

    def test_negative_one_path_one_exon(self):
        '''
            []<------[]
        '''
        path = ['end', str(self.ex1), str(self.ex2), 'start']
        path.reverse()
        self.graph.add_path(path)
        self.transcripts = [path]
        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 0)

    def test_negative_two_path_one_exon(self):
        '''
            []<-------[]
            []<-------------[]
        '''

        path1 = ['end', str(self.ex1), str(self.ex2), 'start']
        path2 = ['end', str(self.ex1), str(self.ex3), 'start']

        path1.reverse()
        path2.reverse()

        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.transcripts = [path1, path2]
        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 2)
        self.assertItemsEqual(get_num_exons(paths), [2, 2])

    def test_negative_two_path_multiple_exon(self):
        '''
            []<---------[]<-------[]<--------[]
            []<--------------------------------------[*]
        '''
        self.ex6 = Exon('chrX', 7000, 8000, 'ex1.1', '-')
        self.ex7 = Exon('chrX', 9000, 10000, 'ex1.1', '-')
        self.exonsDB[str(self.ex6)] = self.ex6
        self.exonsDB[str(self.ex7)] = self.ex7

        path1 = ['end', str(self.ex1), str(self.ex2),
                    str(self.ex3), str(self.ex6), 'start']
        path2 = ['end', str(self.ex1), str(self.ex7), 'start']
        path1.reverse()
        path2.reverse()

        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.transcripts = [path1, path2]

        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 2)
        self.assertItemsEqual(get_num_exons(paths), [4, 2])

    def test_negative_three_path_one_exon(self):
        '''
            []<-----[*]
            []<---------[*]
            []<-------------[*]
        '''

        path1 = ['end', str(self.ex1), str(self.ex2), 'start']
        path2 = ['end', str(self.ex1), str(self.ex3), 'start']
        path3 = ['end', str(self.ex1), str(self.ex5), 'start']
        path1.reverse()
        path2.reverse()
        path3.reverse()

        self.transcripts = [path1, path2, path3]
        self.graph.add_path(path1)
        self.graph.add_path(path2)
        self.graph.add_path(path3)

        paths = list(find_AFE(self.graph, self.exonsDB, self.transcripts))

        self.assertEqual(len(paths[0]), 3)
        self.assertItemsEqual(get_num_exons(paths), [2, 2, 2])

    # def test_negative_three_path_two_exon(self):
    #     '''
    #         []<------[]<------[]
    #         []<---[]<------[]
    #         []<-------[]<-------[]
    #     '''

    #     self.ex4 = Exon('chrX', 7500, 8500, 'ex1.1', '+')
    #     self.ex6 = Exon('chrX', 3500, 4500, 'ex1.1', '+')
    #     self.ex8 = Exon('chrX', 5500, 6500, 'ex1.1', '+')
    #     self.exonsDB[str(self.ex4)] = self.ex4
    #     self.exonsDB[str(self.ex6)] = self.ex6
    #     self.exonsDB[str(self.ex8)] = self.ex8

    #     path1 = ['end', str(self.ex1), str(self.ex2),
    #                 str(self.ex3), 'start']
    #     path2 = ['end', str(self.ex1), str(self.ex5),
    #                 str(self.ex4), 'start']
    #     path3 = ['end', str(self.ex1), str(self.ex6),
    #                 str(self.ex8), 'start']
    #     path1.reverse()
    #     path2.reverse()
    #     path3.reverse()
    #     self.transcripts = [path1, path2, path3]

    #     self.graph.add_path(path1)
    #     self.graph.add_path(path2)
    #     self.graph.add_path(path3)

    #     paths = find_AFE(self.graph, self.exonsDB, self.transcripts)
    #     get_num_exons = [len(path) for path in paths]

    #     self.assertEqual(len(paths), 3)
    #     self.assertItemsEqual(get_num_exons, [3, 3, 3])
