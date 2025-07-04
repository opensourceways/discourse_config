FROM local_discourse/web_only:latest

# 设置目录权限
RUN mkdir -p /shared/state/logrotate && ln -s /shared/state/logrotate /var/lib/logrotate && \
	mkdir -p /shared/state/anacron-spool && ln -s /shared/state/anacron-spool /var/spool/anacron && \
	mkdir -p /shared/uploads && mkdir -p /shared/backups && \
	rm -rf /shared/tmp/{backups,restores} && mkdir -p /shared/tmp/{backups,restores}

# 参考 00-fix-var-logs 文件修改用户权限
RUN rm -f /etc/runit/1.d/00-fix-var-logs && \
    mkdir -p /var/log/nginx && \
    chown -R discourse:www-data /var/log/nginx && \
    chmod -R 644 /var/log/nginx && \
    chmod -R 755 /var/log/nginx && \
    touch /var/log/syslog   && chown -f discourse:www-data /var/log/syslog* && \
    touch /var/log/auth.log && chown -f discourse:www-data /var/log/auth.log* && \
    touch /var/log/kern.log && chown -f discourse:www-data /var/log/kern.log*

# 参考 /etc/service/rsyslog 脚本内容
RUN rm -rf /etc/service/rsyslog

# 参考 /etc/service/unicorn/run, 适配切普通用户的修改
RUN mkdir -p /shared/log/rails && \
    chown -R discourse:www-data /shared/log/rails
COPY ./discourse_config/run /etc/service/unicorn/run
COPY ./discourse_config/00-ensure-links /etc/runit/1.d/00-ensure-links
RUN chmod +x /etc/service/unicorn/run && \
    chmod +x /etc/runit/1.d/00-ensure-links

# 修改 nginx 的启动永华
RUN sed -i "s|www-data|discourse|g" /etc/nginx/nginx.conf

# 修改 discourse 用户shell的umask配置和历史记录设置
RUN echo "umask 0027" >> /home/discourse/.bashrc && \
    echo "set +o history" >> /home/discourse/.bashrc && \
    sed -i "s|HISTSIZE=1000|HISTSIZE=0|" /home/discourse/.bashrc && \
    source /home/discourse/.bashrc

# 限制 discourse 用户的密码有效期
RUN chage --maxdays 30 discourse && \
    passwd -| discourse && \
    usermod -s /sbin/nologin sync

WORKDIR /var/www/discourse
COPY ./discourse_config/rails /usr/local/bin/rails

# 修改权限
RUN chown -R discourse:www-data /etc/runit/1.d && \
    chown -R discourse:www-data /etc/service && \
    chmod -R 755 /etc/service && \
    chown -R discourse:www-data /var/www/discourse && \
    chown -R discourse:www-data /shared && \
    chown -R discourse:www-data /var/log && \
    chown -R discourse:www-data /var/lib && \
    chown -R discourse:www-data /var/run && \
    chown -R discourse:www-data /run && \
    chown -R discourse:www-data /tmp && \
    chown -R discourse:www-data /dev && \
    chown -R discourse:www-data /var/spool && \
    chown -R discourse:www-data /etc/ssl

# 切换到非root用户
USER discourse

# 保留原有的ENTRYPOINT和CMD
# ENTRYPOINT ["sh", "-c", "rails db:migrate && /sbin/boot"]
