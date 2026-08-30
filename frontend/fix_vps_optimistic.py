import re

def optimize_vps():
    with open('src/app/admin/vps/page.tsx', 'r', encoding='utf-8') as f:
        content = f.read()

    new_mut = '''  const statusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: number, status: string }) => {
      const { data } = await api.put(/api/v1/admin/vps-orders//status, { status });
      return data;
    },
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ['admin-vps-orders'] });
      const previousOrders = queryClient.getQueryData(['admin-vps-orders']);
      queryClient.setQueryData(['admin-vps-orders'], (old: any) => 
        old?.map((order: any) => 
          order.id === id ? { ...order, status } : order
        )
      );
      return { previousOrders };
    },
    onError: (err, variables, context) => {
      queryClient.setQueryData(['admin-vps-orders'], context?.previousOrders);
      toast("Failed to update status", 'error');
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
    }
  });'''

    content = re.sub(r'const statusMutation = useMutation\(\{\s*mutationFn: async \(\{ id, status \}: \{ id: number, status: string \}\) => \{\s*const \{ data \} = await api\.put\(/api/v1/admin/vps-orders/\$\{id\}/status, \{ status \}\);\s*return data;\s*\},\s*onSuccess: \(\) => \{\s*queryClient\.invalidateQueries\(\{ queryKey: \[\'admin-vps-orders\'\] \}\);\s*\}\s*\}\);', new_mut, content)
    
    with open('src/app/admin/vps/page.tsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Optimized VPS!")

optimize_vps()
