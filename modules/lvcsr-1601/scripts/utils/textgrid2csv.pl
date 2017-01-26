#!/usr/bin/perl
# textgrid2csv.pl	Converts non-binary Praat TextGrid files to CSV format.
#			Theo Veenker <T.J.G.Veenker@uu.nl>

use strict;
use warnings;
use File::Basename;

use constant INTERVAL	=> 0;
use constant POINT	=> 1;

if ($#ARGV < 0 || $ARGV[0] eq '-h') {
    print "USAGE:\n";
    print "    textgrid2csv.pl [-h] <file> ...\n";
    print "\n";
    print "    Converts non-binary Praat TextGrid files to CSV format.\n";
    print "    For each *.TextGrid file passed it will create a corresponding\n";
    print "    *.csv file. Output files will be overwritten without asking.\n";
    print "\n";
    print "ARGUMENTS:\n";
    print "    -h              show this message and exit\n";
    print "    <file>          text grid text file to convert\n";
    exit 0;
}

sub trim($)
{
    my $s = shift;
    $s =~ s/^\s+//;
    $s =~ s/\s+$//;

    return $s;
}

sub unexpectedEndOfFile
{
    print STDERR "Unexpected end of file.\n";

    return -1;
}

sub parseError($)
{
    my $line = shift;
    print STDERR "Parse error at line $line.\n";

    return -1;
}

sub noTiers
{
    print STDERR "No tiers present.\n";

    return -1;
}

my @lines;
my @tiernames;
my @tiertypes;

my $fnin;
my $fnout;
our $fnbase;
foreach $fnin (@ARGV) {
    if ($fnin =~ /(.*)\.[^\.]+/) {
    	$fnbase = $1;
	$fnout = "$1.csv";
    }
    else {
    	$fnbase = $fnin;
	$fnout = "$fnin.csv";
    }
    print "Converting \"$fnin\" to \"$fnout\".\n";
    if (open(FILEIN, $fnin)) {
	@lines = <FILEIN>;
    	close(FILEIN);
    	if (open(FILEOUT, ">$fnout.tmp")) {
	    @tiernames = ();
	    @tiertypes = ();
	    if (processFile() != 0) {
	    	close(FILEOUT);
		unlink("$fnout.tmp");
	    }
	    else {
	    	close(FILEOUT);
		rename("$fnout.tmp", "$fnout");
	    }
	}
	else {
	    print STDERR "Unable to create \"$fnout.tmp\".\n";
	}
    }
    else {
	print STDERR "Unable to open \"$fnin\".\n";
    }
}
exit;

sub processFile
{
    if (@lines > 3 && $lines[0] =~ /^File type\s*=\s*"ooTextFile"/ &&
    	    $lines[1] =~ /^Object class\s*=\s*"TextGrid"/) {
	if ($lines[3] =~ /^xmin\s*=\s*/ && $lines[4] =~ /^xmax\s*=\s*/) {
    	    return parseNormalTextGrid();
	}
	elsif ($lines[7] =~ /^"IntervalTier"|"TextTier"/) {
    	    return parseShortTextGrid();
	}
    }
    elsif ($lines[0] =~ /^"Praat chronological TextGrid text file"/) {
	return parseChronologicalTextGrid();
    }

    print STDERR "File not recognized as a TextGrid text file.\n";

    return -1;
}

sub parseNormalTextGrid
{
#    print STDERR "Parsing regular TextGrid text file.\n";
    my ($numtiers, $tiernum, $numlabels, $begin, $end, $label, $n);

    my $line = 6;
    return unexpectedEndOfFile() if $line >= @lines;
    if ($lines[$line] =~ /^size\s*=\s*(\d+)/) {
    	$numtiers = int($1);
    }
    else {
    	return parseError($line+1);
    }
    if ($numtiers <= 0) {
    	return noTiers();
    }
    $line += 2;

    for ($tiernum = 1; $tiernum <= $numtiers; $tiernum++) {
    	return unexpectedEndOfFile() if $line >= @lines;
	if ($lines[$line] =~ /^\s*item\s*\[(\d+)\]:/) {
    	    if ($1 != $tiernum) {
    	    	return parseError($line+1);
	    }
	}
	else {
    	    return parseError($line+1);
	}
	$line++;

    	if ($lines[$line] =~ /^\s*class\s*=\s*"IntervalTier"/) {
	    $tiertypes[$tiernum] = INTERVAL;
	    $line++;

    	    return unexpectedEndOfFile() if $line >= @lines;
    	    if ($lines[$line] =~ /^\s*name\s*=\s*(.+)/) {
	    	$tiernames[$tiernum] = trim($1);
	    }
    	    else {
    		return parseError($line+1);
    	    }
	    $line += 3;

	    return unexpectedEndOfFile() if $line >= @lines;
    	    if ($lines[$line] =~ /^\s*intervals:\s*size\s*=\s*(\d+)/) {
	    	$numlabels = int($1);
	    }
    	    else {
    		return parseError($line+1);
    	    }
	    $line++;

	    my $n;
	    for ($n = 1; $n <= $numlabels; $n++) {
	    	return unexpectedEndOfFile() if $line >= @lines;
		if ($lines[$line] =~ /^\s*intervals\s*\[(\d+)\]:/) {
    		    if ($1 != $n) {
    			return parseError($line+1);
		    }
		}
		else {
    		    return parseError($line+1);
		}
		$line++;

    		return unexpectedEndOfFile() if $line >= @lines;
    		if ($lines[$line] =~ /^\s*xmin\s*=\s*([\d\.]+)/) {
	    	    $begin = $1;
		}
    		else {
    		    return parseError($line+1);
    		}
		$line++;

    		return unexpectedEndOfFile() if $line >= @lines;
    		if ($lines[$line] =~ /^\s*xmax\s*=\s*([\d\.]+)/) {
	    	    $end = $1;
		}
    		else {
    		    return parseError($line+1);
    		}
		$line++;

    		return unexpectedEndOfFile() if $line >= @lines;
    		if ($lines[$line] =~ /^\s*text\s*=\s*(.+)/) {
	    	    $label = trim($1);
		}
    		else {
    		    return parseError($line+1);
    		}
		$line++;

	    	printf FILEOUT "\"%s\";%d;%s;%s;%s;%s\n", 
		    basename($fnbase), $tiernum-1, $tiernames[$tiernum], 
		    $begin, $end, $label;
	    }
	}
    	elsif ($lines[$line] =~ /^\s*class\s*=\s*"TextTier"/) {
	    $tiertypes[$tiernum] = POINT;
	    $line++;

    	    return unexpectedEndOfFile() if $line >= @lines;
    	    if ($lines[$line] =~ /^\s*name\s*=\s*(.+)/) {
	    	$tiernames[$tiernum] = trim($1);
	    }
    	    else {
    		return parseError($line+1);
    	    }
	    $line += 3;

	    return unexpectedEndOfFile() if $line >= @lines;
    	    if ($lines[$line] =~ /^\s*points:\s*size\s*=\s*(\d+)/) {
	    	$numlabels = int($1);
	    }
    	    else {
    		return parseError($line+1);
    	    }
	    $line++;

	    my $n;
	    for ($n = 1; $n <= $numlabels; $n++) {
	    	return unexpectedEndOfFile() if $line >= @lines;
		if ($lines[$line] =~ /^\s*points\s*\[(\d+)\]:/) {
    		    if ($1 != $n) {
    			return parseError($line+1);
		    }
		}
		else {
    		    return parseError($line+1);
		}
		$line++;

    		return unexpectedEndOfFile() if $line >= @lines;
    		if ($lines[$line] =~ /^\s*number\s*=\s*([\d\.]+)/) {
	    	    $begin = $1;
		}
    		else {
    		    return parseError($line+1);
    		}
		$line++;

    		return unexpectedEndOfFile() if $line >= @lines;
    		if ($lines[$line] =~ /^\s*mark\s*=\s*(.+)/) {
	    	    $label = trim($1);
		}
    		else {
    		    return parseError($line+1);
    		}
		$line++;

		$end = -1;
	    	printf FILEOUT "\"%s\";%d;%s;%s;%s;%s\n", 
		    $fnbase, $tiernum-1, $tiernames[$tiernum], 
		    $begin, $end, $label;
	    }
	}
    	else {
    	    return parseError($line+1);
    	}
    }

    return 0;
}

sub parseShortTextGrid
{
#    print STDERR "Parsing short TextGrid text file.\n";
    my ($numtiers, $tiernum, $numlabels, $begin, $end, $label, $n);

    my $line = 6;
    return unexpectedEndOfFile() if $line >= @lines;
    if ($lines[$line] =~ /^(\d+)/) {
    	$numtiers = int($1);
    }
    else {
    	return parseError($line+1);
    }
    if ($numtiers <= 0) {
    	return noTiers();
    }
    $line++;

    for ($tiernum = 1; $tiernum <= $numtiers; $tiernum++) {
    	return unexpectedEndOfFile() if $line >= @lines;
    	if ($lines[$line] =~ /^"IntervalTier"/) {
	    $tiertypes[$tiernum] = INTERVAL;
	    $line++;

    	    return unexpectedEndOfFile() if $line >= @lines;
    	    if ($lines[$line] =~ /^\s*(.+)/) {
	    	$tiernames[$tiernum] = trim($1);
	    }
    	    else {
    		return parseError($line+1);
    	    }
	    $line += 3;

	    return unexpectedEndOfFile() if $line >= @lines;
    	    if ($lines[$line] =~ /^(\d+)/) {
	    	$numlabels = int($1);
	    }
    	    else {
    		return parseError($line+1);
    	    }
	    $line++;

	    my $n;
	    for ($n = 1; $n <= $numlabels; $n++) {
    		return unexpectedEndOfFile() if $line >= @lines;
    		if ($lines[$line] =~ /^([\d\.]+)/) {
	    	    $begin = $1;
		}
    		else {
    		    return parseError($line+1);
    		}
		$line++;

    		return unexpectedEndOfFile() if $line >= @lines;
    		if ($lines[$line] =~ /^([\d\.]+)/) {
	    	    $end = $1;
		}
    		else {
    		    return parseError($line+1);
    		}
		$line++;

    		return unexpectedEndOfFile() if $line >= @lines;
    		if ($lines[$line] =~ /^\s*(.+)/) {
	    	    $label = trim($1);
		}
    		else {
    		    return parseError($line+1);
    		}
		$line++;

	    	printf FILEOUT "\"%s\";%d;%s;%s;%s;%s\n", 
		    $fnbase, $tiernum-1, $tiernames[$tiernum], 
		    $begin, $end, $label;
	    }
	}
    	elsif ($lines[$line] =~ /^"TextTier"/) {
	    $tiertypes[$tiernum] = POINT;
	    $line++;

    	    return unexpectedEndOfFile() if $line >= @lines;
    	    if ($lines[$line] =~ /^\s*(.+)/) {
	    	$tiernames[$tiernum] = trim($1);
	    }
    	    else {
    		return parseError($line+1);
    	    }
	    $line += 3;

	    return unexpectedEndOfFile() if $line >= @lines;
    	    if ($lines[$line] =~ /^(\d+)/) {
	    	$numlabels = int($1);
	    }
    	    else {
    		return parseError($line+1);
    	    }
	    $line++;

	    my $n;
	    for ($n = 1; $n <= $numlabels; $n++) {
    		return unexpectedEndOfFile() if $line >= @lines;
    		if ($lines[$line] =~ /^([\d\.]+)/) {
	    	    $begin = $1;
		}
    		else {
    		    return parseError($line+1);
    		}
		$line++;

    		return unexpectedEndOfFile() if $line >= @lines;
    		if ($lines[$line] =~ /^\s*(.+)/) {
	    	    $label = trim($1);
		}
    		else {
    		    return parseError($line+1);
    		}
		$line++;

		$end = -1;
	    	printf FILEOUT "\"%s\";%d;%s;%s;%s;%s\n", 
		    $fnbase, $tiernum-1, $tiernames[$tiernum], 
		    $begin, $end, $label;
	    }
	}
    	else {
    	    return parseError($line+1);
    	}
    }

    return 0;
}

sub parseChronologicalTextGrid
{
#    print STDERR "Parsing chronological TextGrid text file.\n";
    my ($numtiers, $tiernum, $begin, $end, $label);

    my $line = 2;
    return unexpectedEndOfFile() if $line >= @lines;
    if ($lines[$line] =~ /^(\d+)/) {
    	$numtiers = int($1);
    }
    else {
    	return parseError($line+1);
    }
    if ($numtiers <= 0) {
    	return noTiers();
    }
    $line++;

    for ($tiernum = 1; $tiernum <= $numtiers; $tiernum++) {
    	return unexpectedEndOfFile() if $line >= @lines;
    	if ($lines[$line] =~ /^"IntervalTier"\s*(.+)\s+[\d\.]+\s+[\d\.]+/) {
	    $tiernames[$tiernum] = trim($1);
	    $tiertypes[$tiernum] = INTERVAL;
	}
    	elsif ($lines[$line] =~ /^"TextTier"\s*(.+)\s+[\d\.]+\s+[\d\.]+/) {
	    $tiernames[$tiernum] = trim($1);
	    $tiertypes[$tiernum] = POINT;
	}
    	else {
    	    return parseError($line+1);
    	}
	$line++;
    }

    while ($line < @lines) {
    	if ($lines[$line] =~ /^(\d+)\s+/) {
	    $tiernum = int($1);
	    if ($tiernum >= 1 && $tiernum <= @tiernames) {
	    	if ($tiertypes[$tiernum] == INTERVAL) {
    	    	    if ($lines[$line] =~ /^\d+\s+([\d\.]+)\s+([\d\.]+)/) {
	    	    	$begin = $1;
	    	    	$end = $2;
	    	    }
		    else {
    			return parseError($line+1);
		    }
		    $line++;

		    return unexpectedEndOfFile() if $line >= @lines;
    	    	    if ($lines[$line] =~ /^\s*(.+)/) {
	    	    	$label = trim($1);
	    	    }
		    else {
    			return parseError($line+1);
		    }
		}
	    	else {
    	    	    if ($lines[$line] =~ /^\d+\s+([\d\.]+)/) {
	    	    	$begin = $1;
	    	    	$end = -1;
	    	    }
		    else {
    			return parseError($line+1);
		    }
		    $line++;

		    return unexpectedEndOfFile() if $line >= @lines;
    	    	    if ($lines[$line] =~ /^\s*(.+)/) {
	    	    	$label = trim($1);
	    	    }
		    else {
    			return parseError($line+1);
		    }
		}
	    }
	    else {
    		return parseError($line+1);
	    }
	    printf FILEOUT "\"%s\";%d;%s;%s;%s;%s\n", 
		$fnbase, $tiernum-1, $tiernames[$tiernum], 
		$begin, $end, $label;
	}
	else {
    	    return parseError($line+1);
	}
	$line++;
    }

    return 0;
}
