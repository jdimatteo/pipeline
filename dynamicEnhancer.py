#!/usr/bin/python

#131108_dynamicEnhancer.py
#131108
#Charles Lin


#Description:

'''
pipeline to run dynamic enhancer analysis


The MIT License (MIT)

Copyright (c) 2013 Charles Lin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

'''



#================================================================================
#=============================DEPENDENCIES=======================================
#================================================================================

import sys

print "Using python version %s" % sys.version


#importing utils package
sys.path.append('/ark/home/cl512/pipeline/')
import utils
import pipeline_dfci
import os
import time
import string
#================================================================================
#============================GLOBAL PARAMETERS===================================
#================================================================================

#add locations of files and global parameters in this section


dataFile = '/home/clin/projects/131106_seComp/SE_TABLE_FORMATTED.txt'
genome = 'hg18'

dataDict = pipeline_dfci.loadDataTable(dataFile)

#================================================================================
#===================================CLASSES======================================
#================================================================================

#user defined classes here

#================================================================================
#=================================FUNCTIONS======================================
#================================================================================

#write your specific functions here


def makeSECollection(enhancerFile,name,top=0):
    '''
    returns a locus collection from a super table
    top gives the number of rows
    '''
    enhancerTable = utils.parseTable(enhancerFile,'\t')
    superLoci = []

    ticker = 0
    for line in enhancerTable:
        if line[0][0] == '#' or line[0][0] == 'R':
            continue
        else:
            ticker+=1

            superLoci.append(utils.Locus(line[1],line[2],line[3],'.',name+'_'+line[0]))

            if ticker == top:
                break
    return utils.LocusCollection(superLoci,50)

def makeSEDict(enhancerFile,name,superOnly = True):

    '''
    makes an attribute dict for enhancers keyed by uniqueID
    '''

    seDict = {}
    enhancerTable = utils.parseTable(enhancerFile,'\t')

    superLoci = []
    for line in enhancerTable:
        if line[0][0] == '#':
            continue
        if line[0][0] == 'R':
            header = line
            supColumn = header.index('isSuper')
            continue
        if superOnly:
            if int(line[supColumn]) == 1:
                
                signal = float(line[6]) - float(line[7])
                rank = int(line[-2])
                enhancerID = name+'_'+line[0]
                seDict[enhancerID] = {'rank':rank,'signal':signal}

        else:

            signal = float(line[6]) - float(line[7])
            rank = int(line[-2])
            enhancerID = name+'_'+line[0]
            seDict[enhancerID] = {'rank':rank,'signal':signal}

    return seDict


def mergeCollections(superFile1,superFile2,name1,name2,output=''):

    '''
    merges them collections
    '''

    conSuperCollection = makeSECollection(superFile1,name1)

    tnfSuperCollection = makeSECollection(superFile2,name2)


    #now merge them
    mergedLoci = conSuperCollection.getLoci() + tnfSuperCollection.getLoci()

    mergedCollection = utils.LocusCollection(mergedLoci,50)

    #stitch the collection together
    stitchedCollection = mergedCollection.stitchCollection()

    stitchedLoci = stitchedCollection.getLoci()
    
    #loci that are in both get renamed with a new unique identifier

    renamedLoci =[]
    ticker = 1
    for locus in stitchedLoci:

        if len(conSuperCollection.getOverlap(locus)) > 0 and len(tnfSuperCollection.getOverlap(locus)):

            newID = 'CONSERVED_%s' % (str(ticker))
            ticker +=1
            locus._ID = newID
        else:
            locus._ID = locus.ID()[2:]
        renamedLoci.append(locus)

    #now we turn this into a gff and write it out
    gff = utils.locusCollectionToGFF(utils.LocusCollection(renamedLoci,50))

    if len(output) == 0:
        return gff
    else:
        print "writing merged gff to %s" % (output)
        utils.unParseTable(gff,output,'\t')
        return output






#call rose on the mergies

def callRoseMerged(dataFile,mergedGFFFile,name1,name2,parentFolder):

    '''
    makes a rose call for the merged supers
    '''

    

    namesList = [name1]    
    extraMap = [name2,dataDict[name2]['background']]


    return pipeline_dfci.callRose(dataFile,'',parentFolder,namesList,extraMap,mergedGFFFile,tss=0,stitch=0)


def callMergeSupers(superFile1,superFile2,name1,name2,mergedGFFFile,parentFolder):

    '''
    this is the main run function for the script
    all of the work should occur here, but no functions should be defined here
    '''

    mergedGFF = mergeCollections(superFile1,superFile2,name1,name2,mergedGFFFile)

    #call rose on the merged shit    


    roseBashFile = callRoseMerged(dataFile,mergedGFF,name1,name2,parentFolder)
    print('i can has rose bash file %s' % (roseBashFile))

    #run the bash command
    os.system('bash %s' % (roseBashFile))

def callDeltaRScript(mergedGFFFile,parentFolder,name1,name2):

    '''
    runs the R script
    '''
    gffName = mergedGFFFile.split('/')[-1].split('.')[0]
    stitchedFile = "%s%s_ROSE/%s_0KB_STITCHED_ENHANCER_REGION_MAP.txt" % (parentFolder,name1,gffName)
    #print(stitchedFile)

    rcmd = "R --no-save %s %s %s < ./dynamicEnhancer_plot.R" % (stitchedFile,name1,name2)

    return rcmd

def callRankRScript(enhancerRankFile,name1,name2,superFile1,superFile2):

    '''
    runs the R script
    '''

    enhancerCollection1 = makeSECollection(superFile1,name1,False)
    enhancerCollection2 = makeSECollection(superFile2,name2,False)

    nSuper1 = len(enhancerCollection1)
    nSuper2 = len(enhancerCollection2)




    rcmd = "R --no-save %s %s %s %s %s < ./dynamicEnhancer_rank.R" % (enhancerRankFile,name1,name2,nSuper1,nSuper2)

    return rcmd




def callRoseGeneMapper(mergedGFFFile,parentFolder,name1):

    '''
    calls the rose gene mapper w/ 100kb window
    '''
    gffName = mergedGFFFile.split('/')[-1].split('.')[0]
    stitchedFile = "%s%s_ROSE/%s_0KB_STITCHED_ENHANCER_REGION_MAP.txt" % (parentFolder,name1,gffName)
    
    deltaFile = stitchedFile.replace('REGION_MAP','DELTA')
    
    os.chdir('/ark/home/cl512/rose/')
    cmd = 'python ROSE_geneMapper.py -g %s -i %s -w 100000' % (genome,deltaFile)
    os.system(cmd)
    print(cmd)
    


def assignEnhancerRank(enhancerToGeneFile,enhancerFile1,enhancerFile2,name1,name2,rankOutput=''):

    '''
    for all genes in the enhancerToGene Table, assigns the highest overlapping ranked enhancer in the other tables
    '''

    enhancerToGene = utils.parseTable(enhancerToGeneFile,'\t')

    enhancerCollection1 = makeSECollection(enhancerFile1,name1,False)
    enhancerCollection2 = makeSECollection(enhancerFile2,name2,False)

    enhancerDict1 = makeSEDict(enhancerFile1,name1,False)
    enhancerDict2 = makeSEDict(enhancerFile2,name2,False)

    
    #we're going to update the enhancerToGeneTable

    enhancerToGene[0] += ['%s_rank' % name1,'%s_rank' % name2]
    
    for i in range(1,len(enhancerToGene)):

        line = enhancerToGene[i]
        
        locusLine = utils.Locus(line[1],line[2],line[3],'.',line[0])
        
        #if the enhancer doesn't exist, its ranking is dead last on the enhancer list

        enhancer1Overlap = enhancerCollection1.getOverlap(locusLine,'both')
        if len(enhancer1Overlap) == 0:
            enhancer1Rank = len(enhancerCollection1)
        else:
            
            rankList1 = [enhancerDict1[x.ID()]['rank'] for x in enhancer1Overlap]
            enhancer1Rank = min(rankList1)


        enhancer2Overlap = enhancerCollection2.getOverlap(locusLine,'both')
        if len(enhancer2Overlap) == 0:
            enhancer2Rank = len(enhancerCollection2)
        else:
            
            rankList2 = [enhancerDict2[x.ID()]['rank'] for x in enhancer2Overlap]
            enhancer2Rank = min(rankList2)
        enhancerToGene[i]+=[enhancer1Rank,enhancer2Rank]


    if len(rankOutput) == 0:
        return enhancerToGene
    else:
        utils.unParseTable(enhancerToGene,rankOutput,'\t')

#make gain lost gffs

def finishRankOutput(dataFile,rankOutput,genome,mergeFolder,mergeName,name1,name2,cutOff=1.5,window = 100000):

    '''
    cleans up the rank output table
    makes a gff of all of the gained/lost supers beyond
    a certain cutoff w/ a window
    makes a list of gained genes and lost genes
    makes a bed of gained loss
    '''
    dataDict = pipeline_dfci.loadDataTable(dataFile)
    #making sure window and cutoff are int/float
    cutOff = float(cutOff)
    window = int(window)
    genome = string.upper(genome)

    #make the output folder
    outputFolder =pipeline_dfci.formatFolder(mergeFolder+'output/',True)
    
    #bring in the old rank table
    rankEnhancerTable = utils.parseTable(rankOutput,'\t')
    
    #make a new formatted table
    header = rankEnhancerTable[0]
    header[-4] = 'DELTA RANK'
    header[-3] = 'IS_SUPER'
    formattedRankTable =[header]

    #the gffs
    gainedGFF = []
    lostGFF = []

    gainedWindowGFF = []
    lostWindowGFF = []

    #the beds
    gainedTrackHeader = 'track name="%s %s only SEs" description="%s super enhancers that are found only in %s vs %s" itemRGB=On color=255,0,0' % (genome,name2,genome,name2,name1)
    gainedBed = [[gainedTrackHeader]]
    conservedTrackHeader = 'track name="%s %s and %s SEs" description="%s super enhancers that are found in both %s vs %s" itemRGB=On color=0,0,0' % (genome,name1,name2,genome,name1,name2)
    conservedBed = [[conservedTrackHeader]]

    lostTrackHeader = 'track name="%s %s only SEs" description="%s super enhancers that are found only in %s vs %s" itemRGB=On color=0,255,0' % (genome,name1,genome,name1,name2)
    lostBed = [[lostTrackHeader]]

    #the genes
    geneTable =[['GENE','ENHANCER_ID','ENHANCER_CHROM','ENHANCER_START','ENHANCER_STOP',header[6],header[7],header[8],'STATUS']]

    for line in rankEnhancerTable[1:]:
        #fixing the enhancer ID
        line[0] = line[0].replace('_lociStitched','')
        formattedRankTable.append(line)

        #getting the genes
        geneList = []
        geneList += line[9].split(',')
        geneList += line[10].split(',')
        geneList += line[11].split(',')
        geneList = [x for x in geneList if len(x) >0]
        geneList = utils.uniquify(geneList)
        geneString = string.join(geneList,',')

        bedLine = [line[1],line[2],line[3],line[0],line[-4]]
        
        #for gained
        if float(line[6]) > cutOff:
            gffLine = [line[1],line[0],'',line[2],line[3],'','.','',geneString]
            gffWindowLine = [line[1],line[0],'',int(line[2])-window,int(line[3])+window,'','.','',geneString]
            gainedGFF.append(gffLine)
            gainedWindowGFF.append(gffWindowLine)
            geneStatus = name2
            gainedBed.append(bedLine)
        #for lost
        elif float(line[6]) < (-1 * cutOff):
            gffLine = [line[1],line[0],'',line[2],line[3],'','.','',geneString]
            gffWindowLine = [line[1],line[0],'',int(line[2])-window,int(line[3])+window,'','.','',geneString]
            lostGFF.append(gffLine)
            lostWindowGFF.append(gffWindowLine)
            geneStatus = name1
            lostBed.append(bedLine)
        #for conserved
        else:
            geneStatus = 'CONSERVED'
            conservedBed.append(bedLine)

        #now fill in the gene Table
        for gene in geneList:
            geneTableLine = [gene,line[0],line[1],line[2],line[3],line[6],line[7],line[8],geneStatus]
            geneTable.append(geneTableLine)

    #concat the bed
    fullBed = gainedBed + conservedBed + lostBed
            
    #start writing the output
    #there's the two gffs, the bed,the formatted table, the gene table

    #formatted table
    formattedFilename = "%s%s_%s_MERGED_SUPERS_RANK_TABLE.txt" % (outputFolder,genome,mergeName)
    utils.unParseTable(formattedRankTable,formattedFilename,'\t')

    #gffs
    gffFolder = pipeline_dfci.formatFolder(outputFolder+'gff/',True)
    gffFilename_gained = "%s%s_%s_%s_ONLY_SUPERS_-0_+0.gff" % (gffFolder,genome,mergeName,string.upper(name2))
    gffFilenameWindow_gained = "%s%s_%s_%s_ONLY_SUPERS_-%sKB_+%sKB.gff" % (gffFolder,genome,mergeName,string.upper(name2),window/1000,window/1000)

    gffFilename_lost = "%s%s_%s_%s_ONLY_SUPERS_-0_+0.gff" % (gffFolder,genome,mergeName,string.upper(name1))
    gffFilenameWindow_lost = "%s%s_%s_%s_ONLY_SUPERS_-%sKB_+%sKB.gff" % (gffFolder,genome,mergeName,string.upper(name1),window/1000,window/1000)

    utils.unParseTable(gainedGFF,gffFilename_gained,'\t')
    utils.unParseTable(gainedWindowGFF,gffFilenameWindow_gained,'\t')
            
    utils.unParseTable(lostGFF,gffFilename_lost,'\t')
    utils.unParseTable(lostWindowGFF,gffFilenameWindow_lost,'\t')
    
    #bed
    bedFilename = "%s%s_%s_MERGED_SUPERS.bed" % (outputFolder,genome,mergeName)
    utils.unParseTable(fullBed,bedFilename,'\t')

    #geneTable
    geneFilename = "%s%s_%s_MERGED_SUPERS_GENE_TABLE.txt" % (outputFolder,genome,mergeName)
    utils.unParseTable(geneTable,geneFilename,'\t')

    #finally, move all of the plots to the output folder
    cmd = "cp %s%s_ROSE/*.pdf %s%s_%s_MERGED_SUPERS_DELTA.pdf" % (mergeFolder,name1,outputFolder,genome,mergeName)
    os.system(cmd)

    cmd = "cp %s%s_ROSE/*RANK_PLOT.png %s%s_%s_MERGED_SUPERS_RANK_PLOT.png" % (mergeFolder,name1,outputFolder,genome,mergeName)
    os.system(cmd)

    #now execute the bamPlot_turbo.py commands
    bam1 = dataDict[name1]['bam']
    bam2 = dataDict[name2]['bam']
    bamString = "%s,%s" % (bam1,bam2)
    nameString = "%s,%s" % (name1,name2)
    colorString = "0,0,0:100,100,100"

    #change dir
    os.chdir('/ark/home/cl512/pipeline/')
    
    if len(gainedGFF) > 0:
        #gained command
        plotTitle = "%s_ONLY_SE" % (name2)
        cmd = 'python bamPlot_turbo.py -g %s -b %s -i %s -o %s -n %s -c %s -t %s -r -y UNIFORM -p MULTIPLE' % (genome,bamString,gffFilename_gained,outputFolder,nameString,colorString,plotTitle)
        os.system(cmd)

        #gained window command
        plotTitle = "%s_ONLY_SE_%sKB_WINDOW" % (name2,window/1000)
        cmd = 'python bamPlot_turbo.py -g %s -b %s -i %s -o %s -n %s -c %s -t %s -r -y UNIFORM -p MULTIPLE' % (genome,bamString,gffFilenameWindow_gained,outputFolder,nameString,colorString,plotTitle)
        os.system(cmd)

    if len(lostGFF) > 0:
        #lost command
        plotTitle = "%s_ONLY_SE" % (name1)
        cmd = 'python bamPlot_turbo.py -g %s -b %s -i %s -o %s -n %s -c %s -t %s -r -y UNIFORM -p MULTIPLE' % (genome,bamString,gffFilename_lost,outputFolder,nameString,colorString,plotTitle)
        os.system(cmd)

        #lost command
        plotTitle = "%s_ONLY_SE_%sKB_WINDOW" % (name1,window/1000)
        cmd = 'python bamPlot_turbo.py -g %s -b %s -i %s -o %s -n %s -c %s -t %s -r -y UNIFORM -p MULTIPLE' % (genome,bamString,gffFilenameWindow_lost,outputFolder,nameString,colorString,plotTitle)
        os.system(cmd)


    return
    

#================================================================================
#===============================MAIN RUN=========================================
#================================================================================


#write the actual script here

def main(dataFile,genome,mergeFolder,roseFolder1,roseFolder2,name1,name2,mergeName):

    '''
    main run script
    '''

    #part 1

    #start with the all enhancer tables from the initial rose calls
    superFile1 = '%s/%s_peaks_SuperEnhancers.table.txt' % (roseFolder1,name1)
    superFile2 = '%s/%s_peaks_SuperEnhancers.table.txt' % (roseFolder2,name2)

    allFile1 = '%s/%s_peaks_AllEnhancers.table.txt' % (roseFolder1,name1)
    allFile2 = '%s/%s_peaks_AllEnhancers.table.txt' % (roseFolder2,name2)

    #merge the SEs to a gff
    mergedGFFFile = '%s%s_%s_MERGED_SUPERS_-0_+0.gff' % (mergeFolder,string.upper(genome),mergeName)



    parentFolder = mergeFolder
    #callMergeSupers(superFile1,superFile2,name1,name2,mergedGFFFile,parentFolder)
    #time.sleep(300)

    #part2 is the R script
    rcmd = callDeltaRScript(mergedGFFFile,parentFolder,name1,name2)
    print(rcmd) 
    os.system(rcmd)
    time.sleep(30)

    #rank the genes
    
    callRoseGeneMapper(mergedGFFFile,parentFolder,name1)
    time.sleep(300)

    #part 3
    #rank the delta
    gffName = '%s_%s_MERGED_SUPERS_-0_+0' % (string.upper(genome),mergeName)
    enhancerToGeneFile = "%s%s_ROSE/%s_0KB_STITCHED_ENHANCER_DELTA_ENHANCER_TO_GENE_100KB.txt" % (parentFolder,name1,gffName)
    rankOutput = "%s%s_ROSE/%s_0KB_STITCHED_ENHANCER_DELTA_ENHANCER_TO_GENE_100KB_RANK.txt" % (parentFolder,name1,gffName)
    assignEnhancerRank(enhancerToGeneFile,allFile1,allFile2,name1,name2,rankOutput)



    #make the rank plot
    rcmd = callRankRScript(rankOutput,name1,name2,superFile1,superFile2)
    print(rcmd)
    os.system(rcmd)
    
    finishRankOutput(dataFile,rankOutput,genome,mergeFolder,mergeName,name1,name2,cutOff=1,window = 100000)


#=====================================================
#====================786O_H3K27AC=====================
#=====================================================
#786O_H3K27AC
mergeName = '786O_H3K27AC'
mergeFolder = '/home/clin/projects/131106_seComp/mergeAnalysis/%s/' % (mergeName)
mergeFolder = pipeline_dfci.formatFolder(mergeFolder,True)
roseFolder1 = '/home/clin/projects/131106_seComp/rose/786O/786O_H3K27AC_VHL_WT_ROSE/'
roseFolder2 = '/home/clin/projects/131106_seComp/rose/786O/786O_H3K27AC_VHL_NULL_ROSE/'
name1 = '786O_H3K27AC_VHL_WT'
name2 = '786O_H3K27AC_VHL_NULL'


main(dataFile,genome,mergeFolder,roseFolder1,roseFolder2,name1,name2,mergeName)

# #=====================================================
# #====================UMRC2_H3K27AC=====================
# #=====================================================
# #UMRC2_H3K27AC
# mergeName = 'UMRC2_H3K27AC'
# mergeFolder = '/home/clin/projects/131106_seComp/mergeAnalysis/%s/' % (mergeName)
# mergeFolder = pipeline_dfci.formatFolder(mergeFolder,True)
# roseFolder1 = '/home/clin/projects/131106_seComp/rose/UMRC2/UMRC2_H3K27AC_VHL_WT_ROSE/'
# roseFolder2 = '/home/clin/projects/131106_seComp/rose/UMRC2/UMRC2_H3K27AC_VHL_NULL_ROSE/'
# name1 = 'UMRC2_H3K27AC_VHL_WT'
# name2 = 'UMRC2_H3K27AC_VHL_NULL'


# main(dataFile,genome,mergeFolder,roseFolder1,roseFolder2,name1,name2,mergeName)


#=====================================================
#====================RCC4_H3K27AC=====================
#=====================================================
#RCC4_H3K27AC
mergeName = 'RCC4_H3K27AC'
mergeFolder = '/home/clin/projects/131106_seComp/mergeAnalysis/%s/' % (mergeName)
mergeFolder = pipeline_dfci.formatFolder(mergeFolder,True)
roseFolder1 = '/home/clin/projects/131106_seComp/rose/RCC4/RCC4_H3K27AC_VHL_WT_ROSE/'
roseFolder2 = '/home/clin/projects/131106_seComp/rose/RCC4/RCC4_H3K27AC_VHL_NULL_ROSE/'
name1 = 'RCC4_H3K27AC_VHL_WT'
name2 = 'RCC4_H3K27AC_VHL_NULL'


main(dataFile,genome,mergeFolder,roseFolder1,roseFolder2,name1,name2,mergeName)


#=====================================================
#====================RCC4_MED1=====================
#=====================================================
#RCC4_MED1
mergeName = 'RCC4_MED1'
mergeFolder = '/home/clin/projects/131106_seComp/mergeAnalysis/%s/' % (mergeName)
mergeFolder = pipeline_dfci.formatFolder(mergeFolder,True)
roseFolder1 = '/home/clin/projects/131106_seComp/rose/RCC4/RCC4_MED1_VHL_WT_ROSE/'
roseFolder2 = '/home/clin/projects/131106_seComp/rose/RCC4/RCC4_MED1_VHL_NULL_ROSE/'
name1 = 'RCC4_MED1_VHL_WT'
name2 = 'RCC4_MED1_VHL_NULL'


main(dataFile,genome,mergeFolder,roseFolder1,roseFolder2,name1,name2,mergeName)




#=====================================================
#====================A704_H3K27AC=====================
#=====================================================
#A704_H3K27AC
mergeName = 'A704_H3K27AC'
mergeFolder = '/home/clin/projects/131106_seComp/mergeAnalysis/%s/' % (mergeName)
mergeFolder = pipeline_dfci.formatFolder(mergeFolder,True)
roseFolder1 = '/home/clin/projects/131106_seComp/rose/A704/A704_H3K27AC_BAF180_WT_ROSE/'
roseFolder2 = '/home/clin/projects/131106_seComp/rose/A704/A704_H3K27AC_BAF180_NULL_ROSE/'
name1 = 'A704_H3K27AC_BAF180_WT'
name2 = 'A704_H3K27AC_BAF180_NULL'


main(dataFile,genome,mergeFolder,roseFolder1,roseFolder2,name1,name2,mergeName)


#=====================================================
#====================CAKI2_H3K27AC=====================
#=====================================================
#CAKI2_H3K27AC
mergeName = 'CAKI2_H3K27AC'
mergeFolder = '/home/clin/projects/131106_seComp/mergeAnalysis/%s/' % (mergeName)
mergeFolder = pipeline_dfci.formatFolder(mergeFolder,True)
roseFolder1 = '/home/clin/projects/131106_seComp/rose/CAKI2/CAKI2_H3K27AC_BAF180_WT_ROSE/'
roseFolder2 = '/home/clin/projects/131106_seComp/rose/CAKI2/CAKI2_H3K27AC_BAF180_NULL_ROSE/'
name1 = 'CAKI2_H3K27AC_BAF180_WT'
name2 = 'CAKI2_H3K27AC_BAF180_NULL'


main(dataFile,genome,mergeFolder,roseFolder1,roseFolder2,name1,name2,mergeName)


#=====================================================
#====================CAKI2_MED1=====================
#=====================================================
#CAKI2_MED1
mergeName = 'CAKI2_MED1'
mergeFolder = '/home/clin/projects/131106_seComp/mergeAnalysis/%s/' % (mergeName)
mergeFolder = pipeline_dfci.formatFolder(mergeFolder,True)
roseFolder1 = '/home/clin/projects/131106_seComp/rose/CAKI2/CAKI2_MED1_BAF180_WT_ROSE/'
roseFolder2 = '/home/clin/projects/131106_seComp/rose/CAKI2/CAKI2_MED1_BAF180_NULL_ROSE/'
name1 = 'CAKI2_MED1_BAF180_WT'
name2 = 'CAKI2_MED1_BAF180_NULL'


main(dataFile,genome,mergeFolder,roseFolder1,roseFolder2,name1,name2,mergeName)
