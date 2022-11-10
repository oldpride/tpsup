function expect_socket {
    param(
        [Parameter(Mandatory = $true)] [MyConn]$myconn = $null,
        [Parameter(Mandatory = $true)] [string []]$patterns = $null,
        $opt = $null
    )

    $stream = $myconn.stream
    $reader = $myconn.reader
    $writer = $myconn.writer
    $socket = $myconn.socket
    $tcpclient = $myconn.tcpclient

    $data_str = ""
    $num_patterns = $patterns.Count
    $matched = New-Object boolean[] $num_patterns
    $captures = New-Object object[] $num_patterns
    $total_wait = 0
    $this_section_recv = 0;

    while ($tcpclient.Connected) {
        while ($stream.DataAvailable) {
            $size = $stream.Read($buffer,0,$BufferSize)

            if ($size -gt 0) {
                $this_section_recv += $size
                $myconn.in_count += $size
                Write-Verbose "received $size byte(s), total=$($myconn.in_count). this section so far $this_section_recv byte(s)"
                #$text = $encoding.GetString($buffer, 0, $size)
                #$decoded = xor_encode $buffer 'in' $size
                $decoded = $myconn.in_coder.xor($buffer,$size)
                $text = $encoding.GetString($decoded,0,$size)
                $data_str += $text
                Write-Verbose "data_str=$data_str"

                $all_matched = $true

                for ($i = 0; $i -lt $num_patterns; $i++) {
                    if ($matched[$i]) {
                        continue;
                    }
                    # Set-PsDebug -Trace 2
                    # multiline regex use "(?s)"
                    if ($data_str -match "(?s)$($patterns[$i])") {
                        $matched[$i] = $true
                        $captures[$i] = @($Matches[1],$Matches[2],$Matches[3]) # Matches[0] is the whole string
                    } else {
                        $all_matched = $false
                    }
                    # Set-PsDebug -Trace 0                 
                }

                if ($all_matched) {
                    Write-Verbose "`$captures = $(ConvertTo-Json $captures)"
                    return $captures
                }
            } else {
                # this never worked.
                Write-Host $(get_timestamp) "first time happend. remote closed connection"
                exit 1
            }
        }

        # check whether network connection is still connected
        # https://learn-powershell.net/2015/03/29/checking-for-disconnected-connections-with-tcplistener-using-powershell/
        if (($tcpclient.Client.Poll(1,[System.Net.Sockets.SelectMode]::SelectRead) -and
                $tcpclient.Client.Available -eq 0)) {
            $last_words = ""
            if ($data_str -ne "") {
                $tail_size = 100
                if ($data_str.Length -le $tail_size) {
                    $last_words = $data_str
                } else {
                    $last_words = $data_str.SubString($data_str.Length - $tail_size + 1)
                }
            }
            Write-Host "remote side closed connection. Last words: $last_words"
            return $null
        }

        if ($opt["ExpectTimeout"]) {
            if ($total_wait -gt $opt['ExpectTimeout']) {
                $message = "timed out after $($opt['ExpectTimeout']) seconds. very likely wrong protocol. expecting $expected_peer_protocol.*"
                Write-Host $message
                #$encoded = xor_encode [system.Text.Encoding]::Default.GetBytes($message) 'out'
                $encoded = $myconn.out_coder.xor([System.Text.Encoding]::Default.GetBytes($message))
                $writer.Write($encoded)
                $writer.Flush();
                sleep 2; # give a little time so that remote can process this messsage

                for ($i = 0; $i -lt $num_patterns; $i++) {
                    if ($matched[$i]) {
                        Write-Host "   pattern=$($patterns[$i])  matched"
                    } else {
                        Write-Host "   pattern=$($patterns[$i])  didn't matched"
                    }
                }
                return $null
            }
        }
        sleep 1
        $total_wait++
    }
}

