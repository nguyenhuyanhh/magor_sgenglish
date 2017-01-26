#!/usr/bin/perl -w
use strict;
use File::Basename;
use Data::Dumper;

# usage: $0 <stmfile>

my $root = basename($ARGV[0],  ".stm");
my $path = dirname($ARGV[0]);
my $filenameOut = $path . "/". $root .".TextGrid";
print $filenameOut . "\n";

open(IN, $ARGV[0]) or die "Unable to open $ARGV[0]\n";
my @stm=<IN>;
chomp(@stm);
close(IN);

open(OUT, ">$filenameOut") or die "unable to open $filenameOut\n";
print OUT 'File type = "ooTextFile"'."\n". 'Object class = "TextGrid"'."\n\n";

my %output = ();
my $max =0 ;
for my $line (@stm){
	next if ($line =~ m/^;;/);
	my @line = split(/ +/, $line);
	
	my $filename = $line[0];
	my $speaker = $line[2];
	my $start = $line[3];
	my $end = $line[4];
	my $text = join(' ', @line[6 .. $#line]);
	$output{$filename}{$speaker}{$start}{'end'}  = $end ;
	$output{$filename}{$speaker}{$start}{'text'} = $text;
	if ($end >= $max){ $max = $end; }
	
}

foreach my $file (keys %output){
	
	my $speakerNumber = scalar (keys %{$output{$file}});
	print OUT "xmin = 0\n";
	print OUT "xmax = $max\n";
	print OUT 'tiers? <exists>'."\n";
	print OUT 'size = '. $speakerNumber ."\n";
	print OUT 'item []:' ."\n";	
		
	my $spkCnt = 0;		
	foreach my $speaker (keys $output{$file}){
		$spkCnt++;
		print OUT " "x4 ."item [$spkCnt]:\n";
		print OUT " "x8 ."class = \"IntervalTier\"\n";
		print OUT " "x8 ."name = \"$speaker\"\n";
		print OUT " "x8 ."xmin = 0\n";
		print OUT " "x8 ."xmax = $max\n";
		#~ print "" . scalar (keys %{$output{$file}{$speaker}}) . "\n";
		my $intervalCnt = 0;
		my $prevend = 0;

		foreach my $start ( sort {$a <=> $b} keys $output{$file}{$speaker}){
			if ( $prevend < $start ) {
				$intervalCnt++;
			}
			$intervalCnt++;
			$prevend = $output{$file}{$speaker}{$start}{'end'};
		}

		print OUT " "x8 ."intervals: size = $intervalCnt\n";
		$intervalCnt = 0;

		$prevend = 0;

		foreach my $start ( sort {$a <=> $b} keys $output{$file}{$speaker}){
			
			if ( $prevend < $start ) {
				$intervalCnt++;
				print OUT " "x8 ."intervals [$intervalCnt]:\n";
				print OUT " "x12 ."xmin = $prevend\n";
				print OUT " "x12 ."xmax = $start\n";
				print OUT " "x12 ."text = \"--EMPTY--\"\n";
			}

			$intervalCnt++;
			print OUT " "x8 ."intervals [$intervalCnt]:\n";
			print OUT " "x12 ."xmin = $start\n";
			print OUT " "x12 ."xmax = $output{$file}{$speaker}{$start}{'end'}\n";
			print OUT " "x12 ."text = \"$output{$file}{$speaker}{$start}{'text'}\"\n";
			
			$prevend = $output{$file}{$speaker}{$start}{'end'};

		}
	}	
}

close(OUT);
