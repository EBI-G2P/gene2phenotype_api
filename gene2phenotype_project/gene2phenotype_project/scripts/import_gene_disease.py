#!/usr/bin/env python3

import os
import sys
import argparse
import datetime
import MySQLdb


def get_mim_gene_diseases(db_host, db_port, db_name, user, password):
    gene_diseases = {}

    db = MySQLdb.connect(host=db_host, port=db_port, user=user, passwd=password, db=db_name)
    cursor = db.cursor()
    sql = """ SELECT a.value, g.stable_id, x.dbprimary_acc, x.description 
              FROM external_db e, xref x, object_xref o, gene g, gene_attrib a 
              WHERE e.external_db_id = x.external_db_id AND x.xref_id = o.xref_id 
              AND o.ensembl_id = g.gene_id AND e.db_name = 'MIM_MORBID' AND a.gene_id = g.gene_id 
              AND a.attrib_type_id = 4
          """

    sql_variation = """ SELECT pf.object_id, po.accession FROM phenotype_feature pf
                        LEFT JOIN phenotype p ON p.phenotype_id = pf.phenotype_id
                        LEFT JOIN phenotype_ontology_accession po ON po.phenotype_id = pf.phenotype_id
                        LEFT JOIN source s ON s.source_id = pf.source_id
                        WHERE pf.type = 'Gene' AND pf.object_id like 'ENSG%' AND s.name = 'MIM morbid' AND
                        po.accession like 'MONDO%'
                    """

    cursor.execute(sql)
    data = cursor.fetchall()
    if len(data) != 0:
        for row in data:
            if row[0] not in gene_diseases.keys():
                gene_diseases[row[0]] = [{ 'stable_id':row[1],
                                           'mim_id':row[2],
                                           'disease':row[3] }]
            else:
                gene_diseases[row[0]].append({ 'stable_id':row[1],
                                               'mim_id':row[2],
                                               'disease':row[3] })

    db.close()
    return gene_diseases

def insert_gene_diseases(db_host, db_port, db_name, user, password, gene_diseases):
    sql_gene = f""" SELECT l.id, i.identifier FROM locus l
                    LEFT JOIN locus_identifier i on i.locus_id = l.id
                    LEFT JOIN source s on s.id = i.source_id
                    WHERE l.name = %s AND s.name = 'Ensembl'
                """

    sql_source = f""" SELECT id, name FROM source WHERE name = 'OMIM' OR name = 'Mondo' or name = 'Ensembl'
                 """

    sql_insert = f""" INSERT INTO gene_disease(gene_id, disease, identifier, source_id)
                      VALUES(%s, %s, %s, %s)
                  """

    sql_meta = """ INSERT INTO meta(`key`, date_update, is_public, description, source_id, version)
                   VALUES(%s,%s,%s,%s,%s,%s)
               """

    db = MySQLdb.connect(host=db_host, port=db_port, user=user, passwd=password, db=db_name)
    cursor = db.cursor()
    # Fetch source id
    source_ids = {}
    cursor.execute(sql_source)
    data = cursor.fetchall()
    if len(data) != 0:
        for row in data:
            source_ids[row[1]] = row[0]

    for gd, gd_info in gene_diseases.items():
        cursor.execute(sql_gene, [gd])
        data = cursor.fetchall()
        gene_id = None
        gene_stable_id = None
        if len(data) != 0:
            for row in data:
                gene_id = row[0]
                gene_stable_id = row[1]
        if gene_id is not None:
            for info in gd_info:
                disease = info['disease'].split(';')[0]
                if info['stable_id'] == gene_stable_id:
                    cursor.execute(sql_insert, [gene_id, disease, info['mim_id'], source_ids['OMIM']])

    # Insert import info into meta
    cursor.execute(sql_meta, ['import_gene_disease',
                              datetime.datetime.now(),
                              0,
                              'Import OMIM and Mondo gene disease associations',
                              source_ids['Ensembl'],
                              'ensembl_111'])

    db.commit()
    db.close()

def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--host", required=True, help="Ensembl core database host")
    parser.add_argument("--port", required=True, help="Ensembl core host port")
    parser.add_argument("--database", required=True, help="Ensembl core database name")
    parser.add_argument("--user", required=True, help="Username")
    parser.add_argument("--password", default='', help="Password (default: '')")
    parser.add_argument("--g2p_host", required=True, help="G2P database host")
    parser.add_argument("--g2p_port", required=True, help="G2P host port")
    parser.add_argument("--g2p_database", required=True, help="G2P database name")
    parser.add_argument("--g2p_user", required=True, help="Username")
    parser.add_argument("--g2p_password", default='', help="Password (default: '')")

    args = parser.parse_args()

    db_host = args.host
    db_port = int(args.port)
    db_name = args.database
    user = args.user
    password = args.password
    g2p_db_host = args.g2p_host
    g2p_db_port = int(args.g2p_port)
    g2p_db_name = args.g2p_database
    g2p_user = args.g2p_user
    g2p_password = args.g2p_password

    gene_diseases = get_mim_gene_diseases(db_host, db_port, db_name, user, password)
    insert_gene_diseases(g2p_db_host, g2p_db_port, g2p_db_name, g2p_user, g2p_password, gene_diseases)

if __name__ == '__main__':
    main()