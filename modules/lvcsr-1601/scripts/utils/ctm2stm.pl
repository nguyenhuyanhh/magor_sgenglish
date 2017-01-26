#!/usr/bin/perl
use strict;

# File: ctm_segment2stm.pl
# usage $0 <ctm> <segments> <stm>

my $CTMFile = $ARGV[0];
my $segmentFile = $ARGV[1];
my $stmFile = $ARGV[2];
# ====================================================== #
sub MergedData{
	my ($rttmhash, $ctmhash) = @_;
	my %rttmhash = %{$rttmhash};
	foreach my $file (keys %{$rttmhash{DATA}} ) {
	print $file. "\n";
		if (exists($ctmhash->{$file}) ){
			foreach my $rttmdeb ( sort {$a <=> $b} keys %{ $rttmhash->{DATA}{$file}} ){
				my $rttmend = $rttmhash->{DATA}{$file}{$rttmdeb}[1] ;
				my $rttmspkr = $rttmhash->{DATA}{$file}{$rttmdeb}[2] ;
				my @text =();
				foreach my $tbeg (sort {$a <=> $b} keys %{ $ctmhash->{$file} }){
					my $word = $ctmhash->{$file}{$tbeg}[1];
					my $end = $ctmhash->{$file}{$tbeg}[2];
					my $mid = $ctmhash->{$file}{$tbeg}[3];
					if (($mid >= $rttmdeb) and ($mid <= $rttmend)){
						 push @text, $word;
					}
					last if ($tbeg > $end);
				}
				 my $text = join(' ', @text);
				 #print "$file A $rttmspkr $rttmdeb $rttmend <o,f0,male> $text\n";
				 print OUTPUT "$file A $rttmspkr " . sprintf( "%.2f", $rttmdeb) . " ".sprintf( "%.2f", $rttmend) . " <o,f0,male> $text\n";
			 }
		}
	 }
}
1;
# =========================================================== #
sub loadSegmentFile{
	my ($segmentFile, $rttmhash) = @_;
	open(SEGMENT, $segmentFile) or die "Unable to open for read SEGMENT file $segmentFile";
	while(<SEGMENT>){
		chomp;
		my ($tag, $file, $tbeg, $tend) = split(/\s+/,$_,4); 
		my $spkrname = (split(/-/ , $tag))[1];
		$rttmhash->{SPKR}{$file}{$spkrname} = 1;
		push( @{$rttmhash->{DATA}{$file}{$tbeg} }, ($tbeg, $tend, $spkrname));
	}
}
1;
# ====================================================== #
sub loadCTMFile{
	my ($ctmFile, $ctmhash) = @_;
	open(CTM, $ctmFile) or die "Unable to open for read CTM file '$ctmFile'";
	while (<CTM>){
		chomp;
		s/;;.*$//; s/^\s*//; s/\s*$//; next if ($_ =~ /^$/); 
		my ($file, $chnl, $tbeg, $tdur, $ortho) = split(/\s+/,$_,6);
		my $end = sprintf("%.4f", $tbeg+$tdur);
		my $mid = sprintf("%.4f", $tbeg+$tdur/2);
		if ($end <= $tbeg){die "error in $_\n";}
		push( @{ $ctmhash->{$file}{$tbeg} }, ($tbeg, $ortho, $end, $mid));
	}
	close CTM;
}
1;
# ====================================================== #
my %RTTM;
my %CTM;
loadSegmentFile($segmentFile, \%RTTM);
loadCTMFile($CTMFile, \%CTM);
open(OUTPUT, "> $stmFile") or die "unable to open $stmFile\n";
MergedData(\%RTTM, \%CTM); 
close(OUTPUT);

