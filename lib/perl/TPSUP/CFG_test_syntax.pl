our $our_syntax = {
   '^/$' => {
      'cfg'          => { 'type' => 'HASH', 'required' => 1 },
      'package'      => { 'type' => 'SCALAR' },
      'minimal_args' => { 'type' => 'SCALAR' },
   },

   # non-greedy match
   # note: don't use ^/cfg/(.+?)/$, because it will match /cfg/abc/def/ghi/, not only /cfg/abc/
   '^/cfg/([^/]+?)/$' => {
      'base_urls'  => { 'type' => 'ARRAY', 'required' => 1 },
      'op'         => { 'type' => 'HASH',  'required' => 1 },
      'entry'      => { 'type' => 'SCALAR' },
      'entry_func' => { 'type' => 'Union[str, types.CodeType, types.FunctionType]' },
   },
   '^/cfg/([^/]+?)/op/([^/]+?)/$' => {
      'sub_url'   => { 'type' => 'SCALAR', 'required' => 1 },
      'num_args'  => { 'type' => 'SCALAR', 'pattern'  => qr/^\d+$/ },
      'json'      => { 'type' => 'SCALAR', 'pattern'  => qr/^\d+$/ },
      'method'    => { 'type' => 'SCALAR', 'pattern'  => qr/^(GET|POST|DELETE)$/ },
      'Accept'    => { 'type' => 'SCALAR' },
      'comment'   => { 'type' => 'SCALAR' },
      'validator' => { 'type' => 'SCALAR' },
      'post_data' => { 'type' => 'SCALAR' },
      'test_str'  => { 'type' => 'ARRAY' },
   },
};
